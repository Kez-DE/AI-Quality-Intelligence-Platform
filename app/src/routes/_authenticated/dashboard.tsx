import { createFileRoute } from "@tanstack/react-router";
import QualityCockpit from "@/components/QualityCockpit";

export const Route = createFileRoute("/_authenticated/dashboard")({
  component: () => <QualityCockpit />,
});
