import { readFile } from "node:fs/promises";
import { join } from "node:path";

import { StringEnum, Type } from "@earendil-works/pi-ai";
import { defineTool, type ExtensionAPI } from "@earendil-works/pi-coding-agent";

const readCuratedInput = defineTool({
	name: "read_curated_input",
	label: "Read Curated Input",
	description: "Read the sole curated input supplied to this estimation job.",
	parameters: Type.Object({}, { additionalProperties: false }),
	async execute() {
		const text = await readFile(join(process.cwd(), "job-input.json"), "utf-8");
		return { content: [{ type: "text", text }] };
	},
});

const submitEstimate = defineTool({
	name: "submit_estimate",
	label: "Submit Estimate",
	description: "Submit final Estimation Drivers and confidence evidence. This must be your final action.",
	promptSnippet: "Submit final Task Estimation result",
	promptGuidelines: [
		"Use submit_estimate exactly once as the final action for this estimation job.",
		"After calling submit_estimate, do not emit another assistant response in the same turn.",
	],
	parameters: Type.Object(
		{
			drivers: Type.Object(
				{
					files_to_read: Type.Integer({ minimum: 0 }),
					files_to_modify: Type.Integer({ minimum: 0 }),
					expected_turns: Type.Integer({ minimum: 1 }),
					needs_test_run: Type.Boolean(),
				},
				{ additionalProperties: false },
			),
			shadow_token_estimate: Type.Integer({ minimum: 1 }),
			complexity: StringEnum(["simple", "modest", "complex"] as const),
			confidence: Type.Number({ minimum: 0, maximum: 1 }),
			investigation_recommended: Type.Boolean(),
			rationale: Type.String({ maxLength: 8000 }),
			assumptions: Type.Array(Type.String({ maxLength: 4000 }), { maxItems: 50 }),
			risk_flags: Type.Array(Type.String({ maxLength: 4000 }), { maxItems: 50 }),
			budget_note: Type.String({ maxLength: 4000 }),
			source: StringEnum(["llm"] as const),
		},
		{ additionalProperties: false },
	),
	async execute(_toolCallId, params) {
		return {
			content: [{ type: "text", text: "Estimate submitted." }],
			details: params,
			terminate: true,
		};
	},
});

export default function (pi: ExtensionAPI) {
	pi.registerTool(readCuratedInput);
	pi.registerTool(submitEstimate);
}
