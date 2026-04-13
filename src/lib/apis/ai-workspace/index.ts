import { WEBUI_API_BASE_URL } from '$lib/constants';

export type WorkspaceRoute = {
	mode: 'auto';
	task: string;
	task_label: string;
	selected_model_id?: string | null;
	selected_model_name?: string | null;
	required_capabilities: string[];
	features: Record<string, boolean>;
	input_sources: string[];
	workflow: string[];
	confidence: 'low' | 'medium' | 'high';
	memory_recommended: boolean;
	reasons: string[];
	summary: string;
	candidate_models: {
		id: string;
		name: string;
		score: number;
		matched_capabilities: string[];
	}[];
};

export const routeWorkspaceRequest = async (
	token: string,
	body: {
		prompt: string;
		files?: any[];
		selected_model_ids?: string[];
		current_features?: Record<string, boolean>;
	}
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/ai-workspace/route`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify(body)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return (await res.json()) as WorkspaceRoute;
		})
		.catch((err) => {
			console.error(err);
			error = err?.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
