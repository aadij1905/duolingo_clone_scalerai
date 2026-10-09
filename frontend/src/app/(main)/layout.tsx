import Shell from "@/components/Shell";

export default function MainLayout({ children }: LayoutProps<"/">) {
  return <Shell>{children}</Shell>;
}
