# Contact Email And Project Links Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the homepage project cards navigate to their destinations and send the contact form to `pengdeguang2020@qq.com` from an in-app API route.

**Architecture:** Keep the homepage as a client-rendered view, but move email sending into a server-only Next.js route handler. Reuse the existing `projectCards` data for navigation and keep the contact form state local to the contact component so submission, loading, and success/error feedback stay self-contained.

**Tech Stack:** Next.js 14 app router, React 18, TypeScript, Framer Motion, Tailwind CSS, Nodemailer.

## Global Constraints

Use the existing homepage structure and visual language already in the repo. Keep changes focused to the homepage feature area and a small server route. Do not introduce a new global state library.

---

### Task 1: Make project cards navigable

**Files:**
- Modify: `frontend/features/home/homepage-projects.tsx`

**Interfaces:**
- Consumes: `projectCards` entries with `href`
- Produces: clickable project tiles that navigate to the configured route

- [ ] **Step 1: Update the tile to render as a `Link`**

```tsx
import Link from "next/link";

<Link
  key={project.name}
  href={project.href}
  className="group relative flex aspect-square ..."
>
  ...
</Link>
```

- [ ] **Step 2: Keep the motion hover behavior and add a visible focus state**

```tsx
className="group relative flex aspect-square ... outline-none transition duration-500 hover:-translate-y-2 hover:border-cyan-300/35 hover:bg-white/[0.07] focus-visible:ring-2 focus-visible:ring-cyan-300/70"
```

- [ ] **Step 3: Verify the first four cards point to `/`, `/agents/knowledge`, `/agents/browser`, and `/agents/office`**

Run: `rg -n "href: \"/\"|href: \"/agents/knowledge\"|href: \"/agents/browser\"|href: \"/agents/office\"" frontend/features/home/homepage-data.ts`
Expected: four matches for the primary cards.

---

### Task 2: Add hover gradient to roadmap cards

**Files:**
- Modify: `frontend/features/home/homepage-roadmap.tsx`

**Interfaces:**
- Consumes: `roadmapStages`
- Produces: roadmap cards with a hover gradient overlay and slightly richer motion

- [ ] **Step 1: Add a per-card gradient overlay using the existing `motion.article` wrapper**

```tsx
<motion.article className="group relative w-full max-w-[320px] overflow-hidden rounded-[26px] border border-white/10 bg-[linear-gradient(180deg,rgba(15,23,42,0.96),rgba(2,6,23,0.98))] p-5 transition duration-500 hover:-translate-y-1 hover:border-cyan-300/35">
  <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-cyan-400/0 via-cyan-300/0 to-fuchsia-500/0 opacity-0 transition duration-500 group-hover:opacity-100 group-hover:from-cyan-400/20 group-hover:via-sky-300/10 group-hover:to-fuchsia-400/20" />
</motion.article>
```

- [ ] **Step 2: Keep text and separators above the overlay**

```tsx
<div className="relative z-10">
  ...
</div>
```

- [ ] **Step 3: Verify the roadmap still renders three centered cards**

Run: `npm run lint`
Expected: no lint errors.

---

### Task 3: Add a contact email route

**Files:**
- Create: `frontend/lib/mail.ts`
- Create: `frontend/app/api/contact/route.ts`
- Modify: `frontend/package.json`
- Create: `frontend/.env.example`

**Interfaces:**
- Consumes: `name`, `email`, `message`, and a hidden honeypot field from the form
- Produces: `POST /api/contact` that sends a message to `pengdeguang2020@qq.com`

- [ ] **Step 1: Install the email dependency**

```bash
npm install nodemailer
```

- [ ] **Step 2: Add the SMTP helper**

```ts
import nodemailer from "nodemailer";

export function createTransporter() {
  return nodemailer.createTransport({
    host: process.env.SMTP_HOST,
    port: Number(process.env.SMTP_PORT ?? 465),
    secure: Number(process.env.SMTP_PORT ?? 465) === 465,
    auth: {
      user: process.env.SMTP_USER,
      pass: process.env.SMTP_PASS,
    },
  });
}
```

- [ ] **Step 3: Add the API route with validation and a honeypot**

```ts
import { NextResponse } from "next/server";
import { createTransporter } from "@/lib/mail";

export async function POST(request: Request) {
  const body = await request.json();
  if (body.website) return NextResponse.json({ ok: true });
  if (!body.name || !body.email || !body.message) {
    return NextResponse.json({ ok: false, error: "Missing fields" }, { status: 400 });
  }
  const transporter = createTransporter();
  await transporter.sendMail({
    from: process.env.MAIL_FROM,
    to: process.env.CONTACT_TO ?? "pengdeguang2020@qq.com",
    replyTo: body.email,
    subject: `Portfolio contact from ${body.name}`,
    text: `${body.message}\n\nFrom: ${body.name} <${body.email}>`,
  });
  return NextResponse.json({ ok: true });
}
```

- [ ] **Step 4: Add environment variable examples**

```env
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=your@qq.com
SMTP_PASS=your-smtp-app-password
MAIL_FROM=your@qq.com
CONTACT_TO=pengdeguang2020@qq.com
```

- [ ] **Step 5: Verify the route compiles**

Run: `npx tsc --noEmit --pretty false`
Expected: exit code `0`.

---

### Task 4: Wire the contact form to the API

**Files:**
- Modify: `frontend/features/home/homepage-contact.tsx`

**Interfaces:**
- Consumes: `/api/contact`
- Produces: submit/loading/success/error states in the existing contact card

- [ ] **Step 1: Convert the form to controlled submit handling**

```tsx
const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");

async function handleSubmit(event: FormEvent<HTMLFormElement>) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const response = await fetch("/api/contact", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: String(form.get("name") ?? ""),
      email: String(form.get("email") ?? ""),
      message: String(form.get("message") ?? ""),
      website: String(form.get("website") ?? ""),
    }),
  });
  ...
}
```

- [ ] **Step 2: Add a hidden honeypot field and loading copy**

```tsx
<input name="website" tabIndex={-1} autoComplete="off" className="sr-only" />
<button disabled={status === "sending"}>...</button>
```

- [ ] **Step 3: Show success and error feedback inside the card**

```tsx
{status === "sent" ? <p className="text-sm text-emerald-300">Message sent.</p> : null}
{status === "error" ? <p className="text-sm text-rose-300">Failed to send.</p> : null}
```

- [ ] **Step 4: Verify the contact form still renders and submits**

Run: `npm run lint`
Expected: no lint errors.

---

### Task 5: Browser verify the homepage

**Files:**
- None

**Interfaces:**
- Consumes: the running local homepage at `http://localhost:3000/`
- Produces: visual confirmation that project links, roadmap hover styling, and contact form state all render

- [ ] **Step 1: Open the homepage and confirm the project cards are clickable**
- [ ] **Step 2: Confirm the roadmap cards show the new hover gradient treatment**
- [ ] **Step 3: Confirm the contact form has a submit state and no layout regressions**
- [ ] **Step 4: Capture the final verification commands and report exact results**
