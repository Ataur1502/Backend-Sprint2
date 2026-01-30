import secrets
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from .models import User, MFASession

# Duo client is required for the push notification service
try:
    from duo_client import Auth
except Exception:
    Auth = None


MFA_ROLES = ["COLLEGE_ADMIN", "ACADEMIC_COORDINATOR", "college_admin", "accedemic_coordinator"]

def log_debug(msg):
    """Append debug message to a file for analysis."""
    try:
        with open('duo_debug.log', 'a') as f:
            f.write(f"{timezone.now()}: {msg}\n")
    except Exception:
        pass

def _get_mfa_user(email):
    """Internal helper to get user and validate MFA eligibility."""
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return None, 'User not found'
    
    if user.role not in MFA_ROLES:
        return None, 'Role not authorized for MFA'
    return user, None


def send_otp_email(email):
    """
    Create an MFASession and send a verification OTP via email.
    Used for forgot-password flow.
    Returns (success: bool, message: str, mfa_id: str|None)
    """

    user, error = _get_mfa_user(email)
    if error:
        return False, error, None

    now = timezone.now()

    # Get latest MFA session
    latest = MFASession.objects.filter(
        user=user,
        is_verified=False
    ).order_by('-created_at').first()

    # Resend limit check (max 5 resends in 5 minutes)
    if (
        latest
        and latest.resend_count >= 5
        and latest.last_resend_at
        and (now - latest.last_resend_at) < timedelta(minutes=5)
    ):
        return False, 'Resend limit reached. Please try again later.', None

    # ❌ Invalidate all previous OTPs
    MFASession.objects.filter(
        user=user,
        is_verified=False
    ).delete()

    # Generate OTP
    otp = f"{secrets.randbelow(10**6):06d}"

    try:
        # ✅ Create NEW OTP session
        mfa = MFASession.objects.create(
            user=user,
            otp=otp,
            expires_at=now + timedelta(minutes=5),
            resend_count=(latest.resend_count + 1) if latest else 1,
            last_resend_at=now
        )

        subject = 'Your Verification OTP'
        message = f"Your OTP is: {otp}\nIt will expire in 5 minutes."
        from_email = getattr(
            settings,
            'DEFAULT_FROM_EMAIL',
            settings.EMAIL_HOST_USER
        )
        recipient = [user.email]

        send_mail(
            subject,
            message,
            from_email,
            recipient,
            fail_silently=False
        )

        return True, 'OTP sent to email', str(mfa.id)

    except Exception as e:
        try:
            mfa.delete()
        except Exception:
            pass
        return False, str(e), None

def _get_duo_handles(user):
    """Return a priority-ordered list of potential Duo usernames for the user.
    Institutional setups often use email, email prefix, or system username.
    """
    candidates = []
    if user.duo_username: candidates.append(user.duo_username)
    
    # Try email and email prefix (e.g., 'user' from 'user@inst.edu')
    if user.email:
        candidates.append(user.email)
        if '@' in user.email:
            candidates.append(user.email.split('@')[0])
    
    candidates.append(user.username)
    
    # Process candidates: normalize to lowercase and keep original
    final_handles = []
    for c in filter(None, candidates):
        final_handles.append(c)
        final_handles.append(c.lower())
    
    # Return unique list maintaining order
    return list(dict.fromkeys(final_handles))
def send_duo_push(email):
    """Initiate a Duo Push for the user identified by email.
    Tries multiple potential handles (email, username, etc.) safely.
    """
    user, error = _get_mfa_user(email)
    if error:
        return False, error, None

    now = timezone.now()
    latest = MFASession.objects.filter(user=user).order_by('-created_at').first()
    if latest and latest.resend_count >= 5 and latest.last_resend_at and (now - latest.last_resend_at) < timedelta(minutes=5):
        return False, 'Resend limit reached. Please try again later.', None

    # Create session record immediately
    mfa = MFASession.objects.create(user=user, expires_at=now + timedelta(minutes=5))

    if Auth is None or not all([getattr(settings, 'DUO_INTEGRATION_KEY', None), 
                                getattr(settings, 'DUO_SECRET_KEY', None), 
                                getattr(settings, 'DUO_API_HOST', None)]):
        return False, 'Duo service not configured. Please use a passcode from your app.', str(mfa.id)

    try:
        auth_api = Auth(ikey=settings.DUO_INTEGRATION_KEY, 
                        skey=settings.DUO_SECRET_KEY, 
                        host=settings.DUO_API_HOST)
        
        handles = _get_duo_handles(user)
        last_error = "Duo user not found."
        
        for handle in handles:
            try:
                resp = auth_api.auth(username=handle, factor='push', device='auto')
                
                # Handle both nested 'response' format and flat format
                details = resp.get('response', {}) if isinstance(resp, dict) else resp
                if isinstance(resp, dict) and not details and ('result' in resp or 'status' in resp):
                    details = resp
                
                # Check for "user not found" or parameter errors to continue loop
                status_msg = details.get('status_msg', '').lower() if isinstance(details, dict) else str(details).lower()
                if any(x in status_msg for x in ['not found', 'invalid user', 'parameter', 'no device']):
                    last_error = status_msg or last_error
                    continue

                txid = details.get('txid') or details.get('id')
                result = details.get('result') or details.get('status')

                # Check Success FIRST. If it's already allowed, don't wait on txid.
                if result in ('allow', 'approved'):
                    mfa.duo_status = 'allow'
                    mfa.is_verified = True
                    if txid: mfa.duo_txid = txid
                    mfa.save()
                    return True, 'Duo approved', str(mfa.id)

                if txid:
                    mfa.duo_txid = txid
                    mfa.duo_status = 'pending'
                    mfa.save()
                    return True, 'Duo push queued', str(mfa.id)
                
                # If we got this far, this handle *exists* but push might be restricted
                last_error = status_msg
                break # Stop at first legitimate handle found
            except Exception as e:
                err_str = str(e)
                if '400' in err_str or 'parameter' in err_str.lower():
                    continue
                last_error = err_str
                break

        # Map to friendly messages
        friendly_msg = f"Duo Push failed: {last_error}"
        if "restricted" in last_error.lower():
            friendly_msg = "Duo Push is restricted for your phone number based on your institution's Duo policy. " \
                            "Please enter a 6-digit passcode from your Duo Mobile app instead."
        elif "disabled" in last_error.lower():
            friendly_msg = "Your Duo account is currently disabled. Please contact your administrator."
        
        log_debug(f"Duo Failed for {email}. Handles: {handles}. Error: {last_error}")
        return False, friendly_msg, str(mfa.id)

    except Exception as e:
        log_debug(f"Duo Exception for {email}: {str(e)}")
        return False, f'Duo connection error: {str(e)}', str(mfa.id)



def verify_duo_passcode(email, passcode):
    """Verify a 6-digit passcode by trying multiple possible identifiers.
    Returns detailed debug info on failure to help diagnose handle mismatches.
    """
    user, error = _get_mfa_user(email)
    if error: return False, error

    if Auth is None or not all([getattr(settings, 'DUO_INTEGRATION_KEY', None), 
                                getattr(settings, 'DUO_SECRET_KEY', None), 
                                getattr(settings, 'DUO_API_HOST', None)]):
        return False, 'Duo service unavailable'

    # Ensure passcode is clean
    clean_passcode = str(passcode).strip().replace(' ', '')
    
    auth_api = Auth(ikey=settings.DUO_INTEGRATION_KEY, 
                    skey=settings.DUO_SECRET_KEY, 
                    host=settings.DUO_API_HOST)
    
    handles = _get_duo_handles(user)
    best_error = "Duo User not found."
    
    for handle in handles:
        try:
            resp = auth_api.auth(username=handle, factor='passcode', passcode=clean_passcode)
            
            # Handle both nested 'response' format and flat format
            details = resp.get('response', {}) if isinstance(resp, dict) else resp
            if isinstance(resp, dict) and not details and ('result' in resp or 'status' in resp):
                details = resp
            
            result = details.get('result') or details.get('status')
            status_msg = details.get('status_msg', '') if isinstance(details, dict) else str(details)

            if result in ('allow', 'approved'):
                return True, 'Approved'
            
            # If we get a specific error (incorrect passcode, account disabled, etc.)
            # that implies the User matching was successful. STOP and return that error.
            # We ONLY continue if it looks like "User not found".
            is_valid_user = 'incorrect passcode' in status_msg.lower() or 'disabled' in status_msg.lower()
            if is_valid_user:
                return False, f"Duo Denied: {status_msg}"

            # Fallback log logic
            if any(x in status_msg.lower() for x in ['not found', 'invalid user', 'parameter']):
                if best_error == "Duo User not found.":
                    best_error = status_msg or best_error
                continue
            
            # If it's some other error, update best_error
            best_error = status_msg or best_error
                
        except Exception as e:
            err_str = str(e)
            log_debug(f"Duo Passcode Exception for handle {handle}: {err_str}")
            if '400' in err_str or 'parameter' in err_str.lower():
                continue
            if best_error == "Duo User not found.":
                best_error = err_str
            
    log_debug(f"Duo Passcode Failed for {email}. Best Error: {best_error}. Handles: {handles}")
    return False, f'Duo Denied: {best_error}'


def check_duo_status(mfa_id):
    """Poll Duo for status. Enhanced to handle diverse response structures."""
    try:
        mfa = MFASession.objects.get(id=mfa_id)
    except MFASession.DoesNotExist:
        return 'error', 'MFA session not found', None

    if mfa.is_verified:
        return 'allow', 'already verified', mfa

    if not mfa.duo_txid:
        return 'error', 'No Duo transaction associated', mfa

    if Auth is None or not all([getattr(settings, 'DUO_INTEGRATION_KEY', None), 
                                getattr(settings, 'DUO_SECRET_KEY', None), 
                                getattr(settings, 'DUO_API_HOST', None)]):
        return 'error', 'Duo config missing or library not installed', mfa

    auth_api = Auth(ikey=settings.DUO_INTEGRATION_KEY, 
                    skey=settings.DUO_SECRET_KEY, 
                    host=settings.DUO_API_HOST)
    try:
        resp = None
        # Try known status methods on the Auth API
        for method in ('auth_status', 'status', 'auth_check'):
            fn = getattr(auth_api, method, None)
            if fn:
                try:
                    # Some versions use txid=, some use first positional arg
                    resp = fn(mfa.duo_txid)
                    break
                except TypeError:
                    try:
                        resp = fn(txid=mfa.duo_txid)
                        break
                    except Exception:
                        continue
        if resp is None:
            return 'error', 'Duo status method call failed', mfa

        # Extract status from Duo response
        res_data = resp.get('response', {}) if isinstance(resp, dict) else {}
        # If 'response' is missing but 'result' or 'status' is at top level
        if not res_data and isinstance(resp, dict):
            res_data = resp
            
        status = res_data.get('result') or res_data.get('status') or res_data.get('tx_status')
        
        if status in ('allow', 'approved'):
            mfa.duo_status = 'allow'
            mfa.is_verified = True
            mfa.save()
            return 'allow', 'approved', mfa
        
        if status in ('deny', 'denied'):
            mfa.duo_status = 'deny'
            mfa.save()
            return 'deny', res_data.get('status_msg', 'denied'), mfa

        return 'pending', 'waiting for user action', mfa

    except Exception as e:
        return 'error', f'Duo polling error: {str(e)}', mfa
