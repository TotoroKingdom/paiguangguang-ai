import nodemailer from "nodemailer";

function getRequiredEnv(name: string) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required env var: ${name}`);
  }
  return value;
}

export function createContactTransporter() {
  const host = getRequiredEnv("SMTP_HOST");
  const user = getRequiredEnv("SMTP_USER");
  const pass = getRequiredEnv("SMTP_PASS");
  const port = Number(process.env.SMTP_PORT ?? 465);

  return nodemailer.createTransport({
    host,
    port,
    secure: port === 465,
    auth: {
      user,
      pass
    }
  });
}

export function getContactRecipient() {
  return process.env.CONTACT_TO || "pengdeguang2020@qq.com";
}

export function getMailFrom() {
  return process.env.MAIL_FROM || process.env.SMTP_USER || "";
}
