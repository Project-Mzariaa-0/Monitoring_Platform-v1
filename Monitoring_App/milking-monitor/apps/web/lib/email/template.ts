function escapeHtml(value: string): string {
  return value.replace(/[<>&"]/g, (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;" }[c] ?? c));
}

export function verificationEmailHtml(input: { name: string; verifyUrl: string; logoUrl: string }): string {
  const safeName = escapeHtml(input.name);
  return `<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#F7F5EF;font-family:Arial,Helvetica,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F7F5EF;padding:32px 16px;">
<tr><td align="center">
<table role="presentation" width="560" cellpadding="0" cellspacing="0" style="background:#FFFFFF;border-radius:12px;overflow:hidden;">
<tr><td style="background:#1F4D3A;padding:24px;text-align:center;">
<img src="${input.logoUrl}" alt="Milking Monitor" width="120" style="display:block;margin:0 auto;max-height:64px;" />
<div style="color:#F7F5EF;font-size:18px;font-weight:bold;margin-top:12px;">Milking Monitor</div>
</td></tr>
<tr><td style="padding:32px 28px;color:#20261F;">
<h1 style="font-size:22px;margin:0 0 12px;">Verify your email, ${safeName}</h1>
<p style="font-size:14px;line-height:1.6;margin:0 0 20px;">Thanks for creating a Milking Monitor account. Confirm your email address to activate your login:</p>
<p style="text-align:center;margin:0 0 20px;"><a href="${input.verifyUrl}" style="display:inline-block;padding:12px 32px;background:#1F4D3A;color:#FFFFFF;text-decoration:none;border-radius:8px;font-weight:bold;font-size:15px;">Verify email</a></p>
<p style="font-size:13px;color:#5C6B5D;line-height:1.6;margin:0 0 8px;">This link expires in 24 hours. If you did not create this account, ignore this email.</p>
<p style="font-size:12px;color:#8B968B;line-height:1.6;margin:0;">If the button does not work, paste this link into your browser:<br />${input.verifyUrl}</p>
</td></tr>
<tr><td style="padding:16px 28px;background:#EFEDE4;text-align:center;font-size:12px;color:#8B968B;">Milking Monitor &middot; Cooperative Dairy Unit</td></tr>
</table>
</td></tr>
</table>
</body>
</html>`;
}

export function verificationEmailText(input: { name: string; verifyUrl: string }): string {
  return `Hi ${input.name},\n\nThanks for creating a Milking Monitor account. Verify your email within 24 hours:\n\n${input.verifyUrl}\n\nIf you did not create this account, ignore this email.`;
}
