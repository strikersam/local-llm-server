export default function HeroSection() {
  return (
    <section className="auth-shell__hero flex min-h-[592px] w-full items-start justify-start px-4">
      <div className="auth-shell__brand flex items-center gap-2 mb-6">
        <img src="/logos/logo-only.svg" alt="" width="24" height="24" aria-hidden="true" />
        <span className="auth-shell__brand-name text-xl font-semibold">CompanyHelm</span>
      </div>
      <h1 className="text-3xl font-bold mb-4">Welcome to CompanyHelm.</h1>
      <p className="text-lg text-muted-foreground">
        Coordinate agents, tasks, chats, and execution environments from one operator workspace built for teams shipping real work with AI.
      </p>
    </section>
  );
}
