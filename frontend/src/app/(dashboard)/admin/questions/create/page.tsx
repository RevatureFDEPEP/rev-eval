import { redirect } from "next/navigation";

type AdminCreateQuestionPageProps = {
  searchParams?:
    | Promise<Record<string, string | string[] | undefined>>
    | Record<string, string | string[] | undefined>;
};

function toQueryString(
  searchParams: Record<string, string | string[] | undefined> | undefined,
): string {
  const params = new URLSearchParams();

  Object.entries(searchParams ?? {}).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      value.forEach((entry) => params.append(key, entry));
      return;
    }

    if (typeof value === "string") {
      params.set(key, value);
    }
  });

  return params.toString();
}

export default async function AdminCreateQuestionPage({
  searchParams,
}: AdminCreateQuestionPageProps) {
  const resolvedSearchParams = await Promise.resolve(searchParams);
  const queryString = toQueryString(resolvedSearchParams);

  redirect(`/trainer/questions/create${queryString ? `?${queryString}` : ""}`);
}
