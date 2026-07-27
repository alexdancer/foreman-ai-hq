import { readFile } from "node:fs/promises";
import { join } from "node:path";

import { StringEnum, Type } from "@earendil-works/pi-ai";
import { defineTool, type ExtensionAPI } from "@earendil-works/pi-coding-agent";

const readCuratedInput = defineTool({
	name: "read_curated_input",
	label: "Read Curated Input",
	description: "Read the sole curated input supplied to this agent-review job.",
	parameters: Type.Object({}, { additionalProperties: false }),
	async execute() {
		const text = await readFile(join(process.cwd(), "job-input.json"), "utf-8");
		return { content: [{ type: "text", text }] };
	},
});

const finding = Type.Object(
	{
		severity: StringEnum(["critical", "high", "medium", "low", "info"] as const),
		message: Type.String({ minLength: 1, maxLength: 8000 }),
		path: Type.Optional(Type.String({ maxLength: 2000 })),
		line: Type.Optional(Type.Integer({ minimum: 1 })),
	},
	{ additionalProperties: false },
);

const submitReview = defineTool({
	name: "submit_review",
	label: "Submit Review",
	description: "Submit final Agent Review result. This must be your final action.",
	promptSnippet: "Submit final Agent Review result",
	promptGuidelines: [
		"Use submit_review exactly once as the final action for this agent-review job.",
		"After calling submit_review, do not emit another assistant response in the same turn.",
	],
	parameters: Type.Object(
		{
			summary: Type.String({ minLength: 1, maxLength: 8000 }),
			recommendation: StringEnum(["approve", "needs_changes", "block"] as const),
			findings: Type.Array(finding, { maxItems: 50 }),
		},
		{ additionalProperties: false },
	),
	async execute(_toolCallId, params) {
		return {
			content: [{ type: "text", text: "Review submitted." }],
			details: params,
			terminate: true,
		};
	},
});

export default function (pi: ExtensionAPI) {
	pi.registerTool(readCuratedInput);
	pi.registerTool(submitReview);
}
