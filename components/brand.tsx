import Link from "next/link";

export function Brand() {
  return (
    <Link href="/" className="flex items-center gap-2" aria-label="MediNaija home">
      <span className="grid h-10 w-10 place-items-center rounded-xl bg-green-600 text-lg font-bold text-white">M</span>
      <span>
        <span className="block font-serif text-xl font-semibold text-green-900">MediNaija</span>
        <span className="hidden text-xs text-green-700 sm:block">Chronic care, made simpler</span>
      </span>
    </Link>
  );
}
