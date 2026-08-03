import { readFile } from "node:fs/promises";
import { join } from "node:path";

import { StringEnum, Type } from "@earendil-works/pi-ai";
import { defineTool, type ExtensionAPI } from "@earendil-works/pi-coding-agent";

const readCuratedInput = defineTool({
	name: "read_curated_input",
	label: "Read Curated Input",
	description: "Read the sole curated input supplied to this intake decision job.",
	parameters: Type.Object({}, { additionalProperties: false }),
	async execute() {
		const text = await readFile(join(process.cwd(), "job-input.json"), "utf-8");
		return { content: [{ type: "text", text }] };
	},
});

const submitIntake = defineTool({
	name: "submit_intake",
	label: "Submit Intake Decision",
	description: "Submit the final intake routing decision. This must be your final action.",
	promptSnippet: "Submit final intake decision",
	promptGuidelines: [
		"Use submit_intake exactly once as the final action for this intake decision job.",
		"After calling submit_intake, do not emit another assistant response in the same turn.",
	],
	parameters: Type.Object(
		{
			decision: StringEnum(["single_task", "needs_breakdown"] as const),
			reason: Type.String({ maxLength: 2000 }),
		},
		{ additionalProperties: false },
	),
	async execute(_toolCallId, params) {
		return {
			content: [{ type: "text", text: "Intake decision submitted." }],
			details: params,
			terminate: true,
		};
	},
});

export default function (pi: ExtensionAPI) {
	pi.registerTool(readCuratedInput);
	pi.registerTool(submitIntake);
}
