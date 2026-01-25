/** @type {import('next').NextConfig} */
const nextConfig = {
  /* config options here */
  experimental: {
    // Setting this to silence workspace root warnings and potential reload loops
    turbopack: {
      root: '.',
    },
  },
};

export default nextConfig;
