/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ['@mapbox/tiny-sdf'],
  experimental: {
    esmExternals: 'loose'
  }
}
module.exports = nextConfig;
