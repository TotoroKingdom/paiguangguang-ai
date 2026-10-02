import { ArrowUpRightIcon, GithubIcon, MailIcon } from "@/components/icons";
import { homepageContact, homepageContactLinks } from "./homepage-data";

export function HomepageContact() {
  return (
    <section id="contact" className="brand-section brand-contact scroll-mt-24" aria-labelledby="contact-title">
      <div className="brand-contact__layout">
        <div>
          <p className="brand-eyebrow">联系我</p>
          <h2 id="contact-title" className="brand-contact__title">{homepageContact.title}</h2>
        </div>

        <div className="brand-contact__side">
          <p className="brand-contact__description">{homepageContact.description}</p>
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
