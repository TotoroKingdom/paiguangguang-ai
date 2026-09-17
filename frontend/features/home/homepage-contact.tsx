import { ArrowUpRightIcon, GithubIcon, MailIcon } from "@/components/icons";

export function HomepageContact() {
  return (
    <section id="contact" className="brand-section brand-contact scroll-mt-24">
      <div className="brand-contact__layout">
        <div>
          <p className="brand-eyebrow">Contact</p>
          <h2 className="brand-contact__title">Build useful AI systems together.</h2>
        </div>

        <div className="brand-contact__side">
          <p className="brand-contact__description">如果你正在构建需要知识、行动与可靠交付的 AI 产品，欢迎联系我。</p>
          <div className="brand-contact__links">
            <a href="mailto:totorokingdom@foxmail.com" className="brand-contact__link">
              <span>
                <MailIcon size={16} />
                Email
              </span>
              <ArrowUpRightIcon size={16} />
            </a>
            <a
              href="https://github.com/TotoroKingdom"
              rel="noreferrer"
              target="_blank"
              className="brand-contact__link"
            >
              <span>
                <GithubIcon size={16} />
                GitHub
              </span>
              <ArrowUpRightIcon size={16} />
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
