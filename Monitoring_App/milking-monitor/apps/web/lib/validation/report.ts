import { z } from "zod";

export const generateReportSchema = z.object({
  session_id: z.string().uuid(),
});

export type GenerateReportInput = z.infer<typeof generateReportSchema>;
