type SectionTitleProps = {
  eyebrow: string;
  title: string;
  description?: string;
};

export function SectionTitle({ eyebrow, title, description }: SectionTitleProps) {
  return (
    <div className="space-y-4">
      <p className="text-sm font-semibold uppercase tracking-[0.32em] text-cyan-200/80">{eyebrow}</p>
      <h2 className="bg-gradient-to-r from-white via-cyan-100 to-fuchsia-200 bg-clip-text text-3xl font-black text-transparent sm:text-5xl">
        {title}
      </h2>
      <div className="h-1 w-24 rounded-full bg-gradient-to-r from-cyan-400 via-sky-400 to-fuchsia-400" />
      {description ? <p className="max-w-3xl text-base leading-8 text-slate-300">{description}</p> : null}
    </div>
  );
}
