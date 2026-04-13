import { PersonaClient } from "@/components/sections/PersonaClient";

export async function generateStaticParams() {
  return [
    { persona: 'founders' },
    { persona: 'consultants' },
    { persona: 'coaches' },
    { persona: 'agencies' },
  ];
}

export default async function PersonaPage({ params }: { params: Promise<{ persona: string }> }) {
  const { persona } = await params;
  return <PersonaClient persona={persona} />;
}
