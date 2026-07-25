import { readFile } from "node:fs/promises";
import { join } from "node:path";

import { StringEnum, Type } from "@earendil-works/pi-ai";
import { defineTool, type ExtensionAPI } from "@earendil-works/pi-coding-agent";

const readCuratedInput = defineTool({
	name: "read_curated_input",
	label: "Read Curated Input",
	description: "Read the sole curated input supplied to this task-breakdown job.",
	parameters: Type.Object({}, { additionalProperties: false }),
	async execute() {
		const text = await readFile(join(process.cwd(), "job-input.json"), "utf-8");
		return { content: [{ type: "text", text }] };
	},
});

const textOrStrings = Type.Union([
	Type.String({ maxLength: 20000 }),
	Type.Array(Type.String({ maxLength: 8000 }), { maxItems: 50 }),
]);

const candidate = Type.Object(
	{
		kind: StringEnum(["implementation", "scout", "acceptance_verification"] as const),
		title: Type.String({ minLength: 1, maxLength: 500 }),
		objective: Type.String({ minLength: 1, maxLength: 8000 }),
		prompt: Type.String({ minLength: 1, maxLength: 20000 }),
		acceptance_criteria: textOrStrings,
		constraints: textOrStrings,
		proof: Type.String({ minLength: 1, maxLength: 8000 }),
		why_this_task_exists: Type.String({ minLength: 1, maxLength: 4000 }),
		why_not_smaller: Type.String({ minLength: 1, maxLength: 4000 }),
		why_not_larger: Type.String({ minLength: 1, maxLength: 4000 }),
		dependencies: textOrStrings,
		likely_entry_points: textOrStrings,
		target_task_id: Type.Optional(Type.Union([Type.String({ maxLength: 200 }), Type.Null()])),
		execution_mode: StringEnum(["AFK", "HITL"] as const),
		hitl_reason: Type.String({ maxLength: 4000 }),
		human_in_loop: Type.Boolean(),
	},
	{ additionalProperties: false },
);

const submitBreakdown = defineTool({
	name: "submit_breakdown",
	label: "Submit Breakdown",
	description: "Submit final Proposed Task Breakdown contract. This must be your final action.",
	promptSnippet: "Submit final Task Breakdown result",
	promptGuidelines: [
		"Use submit_breakdown exactly once as the final action for this task-breakdown job.",
		"After calling submit_breakdown, do not emit another assistant response in the same turn.",
	],
	parameters: Type.Object(
		{
			decision: StringEnum(["single_task", "proposed_task_breakdown"] as const),
			candidates: Type.Array(candidate, { minItems: 1, maxItems: 20 }),
			rejected_items: Type.Array(
				Type.Object(
					{
						text: Type.String({ minLength: 1, maxLength: 8000 }),
						reason: Type.String({ minLength: 1, maxLength: 4000 }),
					},
					{ additionalProperties: false },
				),
				{ maxItems: 50 },
			),
			global_contract_summary: Type.String({ maxLength: 20000 }),
			global_constraints: textOrStrings,
			verification: textOrStrings,
			non_goals: textOrStrings,
			recommended_sequence: textOrStrings,
			confidence: Type.Number({ minimum: 0, maximum: 1 }),
			rationale: Type.String({ maxLength: 8000 }),
			source: Type.Optional(StringEnum(["llm"] as const)),
		},
		{ additionalProperties: false },
	),
	async execute(_toolCallId, params) {
		return {
			content: [{ type: "text", text: "Task breakdown submitted." }],
			details: params,
			terminate: true,
		};
	},
});

export default function (pi: ExtensionAPI) {
	pi.registerTool(readCuratedInput);
	pi.registerTool(submitBreakdown);
}
