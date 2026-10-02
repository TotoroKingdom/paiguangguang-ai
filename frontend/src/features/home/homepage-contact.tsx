import { ArrowUpRightIcon, GithubIcon, MailIcon } from "@/components/icons";
import { homepageContactLinks } from "./homepage-data";

export function HomepageContact() {
  return (
    <section id="contact" className="brand-section brand-contact scroll-mt-24" aria-labelledby="contact-title">
      <div className="brand-contact__layout">
        <div>
          <p className="brand-eyebrow">联系我</p>
          <h2 id="contact-title" className="brand-contact__title">一起把 AI，做成真正有用的产品。</h2>
        </div>

        <div className="brand-contact__side">
          <p className="brand-contact__description">如果你正在构建需要知识、行动与可靠交付的 AI 产品，欢迎联系我。</p>
          <div className="brand-contact__links">
            {homepageContactLinks.map((link) => {
              const external = link.href.startsWith("https://");
              return (
                <a key={link.href} href={link.href} target={external ? "_blank" : undefined} rel={external ? "noopener noreferrer" : undefined} className="brand-contact__link">
                  <span>{external ? <GithubIcon size={16} /> : <MailIcon size={16} />}{link.label === "GitHub" ? link.label : "邮箱"}</span>
                  <ArrowUpRightIcon size={16} />
                  {external && <span className="sr-only">（新标签页打开）</span>}
                </a>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
