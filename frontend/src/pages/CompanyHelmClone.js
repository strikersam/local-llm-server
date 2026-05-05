import React from 'react';
import HeroSection from '../components/HeroSection';
import PanelSection from '../components/PanelSection';

export default function CompanyHelmClone() {
  return (
    <div className="min-h-[100dvh] w-full bg-[#0F0F13] relative overflow-hidden">
      {/* Background gradient - same as LoginPage */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-[-20%] left-[-10%] w-[600px] h-[600px] rounded-full bg-[#002FA7]/8 blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-5%] w-[400px] h-[400px] rounded-full bg-[#002FA7]/5 blur-[100px]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,rgba(0,47,167,0.04),transparent_60%)]" />
        <div
          className="absolute inset-0 opacity-[0.015]"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='32' height='32' viewBox='0 0 32 32' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M0 0h1v1H0V0zm16 16h1v1h-1v-1z' fill='%23ffffff' fill-opacity='1'/%3E%3C/svg%3E")`,
            backgroundSize: '32px 32px',
          }}
        />
      </div>

      {/* Main content */}
      <div className="flex min-h-[100dvh] w-full items-center justify-center px-4">
        <div className="w-full max-w-[1024px] mx-auto">
          <HeroSection />
          <PanelSection />
        </div>
      </div>
    </div>
  );
}
