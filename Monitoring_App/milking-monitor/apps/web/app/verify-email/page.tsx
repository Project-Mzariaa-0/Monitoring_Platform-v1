import VerifyEmailClient from "./verify-client";

export default async function VerifyEmailPage({
  searchParams,
}: {
  searchParams: Promise<{ email?: string; token?: string }>;
}) {
  const params = await searchParams;
  return <VerifyEmailClient email={params.email ?? ""} token={params.token ?? ""} />;
}
