<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { updateUserSettings } from '$lib/apis/users';
	import { config, models, settings, user } from '$lib/stores';
	import type { WorkspaceRoute } from '$lib/apis/ai-workspace';

	const i18n = getContext('i18n');

	export let route: WorkspaceRoute | null = null;
	export let mode: 'auto' | 'manual' = 'auto';
	export let selectedModelNames: string[] = [];
	export let compact = false;
	export let showCapabilities = false;

	const featureLabel = (feature: string) =>
		({
			web_search: 'Web search',
			image_generation: 'Image generation',
			code_interpreter: 'Code interpreter',
			memory: 'Memory'
		})[feature] ?? feature.replaceAll('_', ' ');

	const sourceLabel = (source: string) =>
		({
			text: 'Text',
			image: 'Image',
			audio: 'Audio',
			file: 'Files',
			link: 'Web links'
		})[source] ?? source;

	const taskLabel = (task: string) =>
		({
			general_chat: 'General chat',
			file_analysis: 'File Q&A',
			image_analysis: 'Vision analysis',
			image_generation: 'Image generation',
			image_editing: 'Image editing',
			audio_workflow: 'Voice and audio',
			web_research: 'Web research',
			link_parsing: 'Link parsing',
			deep_research: 'Deep research'
		})[task] ?? task.replaceAll('_', ' ');

	const confidenceClass = (confidence: WorkspaceRoute['confidence'] | null | undefined) =>
		({
			high: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/70 dark:text-emerald-200',
			medium: 'bg-amber-100 text-amber-700 dark:bg-amber-950/70 dark:text-amber-200',
			low: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200'
		})[confidence ?? 'medium'];

	const featurePillClass = (enabled: boolean) =>
		enabled
			? 'bg-sky-100 text-sky-700 dark:bg-sky-950/70 dark:text-sky-200'
			: 'bg-gray-100 text-gray-500 dark:bg-gray-850 dark:text-gray-400';

	let capabilityCards = [];
	let selectedModelSummary = '';
	let enabledFeatures = [];
	let routeSources = [];
	let canToggleMemory = false;

	$: selectedModelSummary =
		selectedModelNames.filter((name) => name).length > 0
			? selectedModelNames.join(', ')
			: $i18n.t('Model will be chosen automatically');

	$: enabledFeatures = Object.entries(route?.features ?? {}).filter(([, enabled]) => enabled);
	$: routeSources = (route?.input_sources ?? []).map((source) => sourceLabel(source));
	$: canToggleMemory =
		($config?.features?.enable_memories ?? false) &&
		($user?.role === 'admin' || ($user?.permissions?.features?.memory ?? true));
	$: capabilityCards = [
		{
			id: 'text',
			label: 'Text',
			description: 'Draft, answer and reason',
			available: true
		},
		{
			id: 'voice',
			label: 'Voice',
			description: 'Dictation and voice mode',
			available: $user?.role === 'admin' || ($user?.permissions?.chat?.stt ?? true)
		},
		{
			id: 'images',
			label: 'Images',
			description: 'Analyze and generate visuals',
			available:
				$models.some((model) => model?.info?.meta?.capabilities?.vision ?? true) ||
				(($config?.features?.enable_image_generation ?? false) &&
					($user?.role === 'admin' || $user?.permissions?.features?.image_generation))
		},
		{
			id: 'files',
			label: 'Files',
			description: 'Ask questions on documents',
			available: $user?.role === 'admin' || ($user?.permissions?.chat?.file_upload ?? true)
		},
		{
			id: 'web',
			label: 'Web',
			description: 'Search and parse links',
			available:
				($config?.features?.enable_web_search ?? false) &&
				($user?.role === 'admin' || $user?.permissions?.features?.web_search)
		},
		{
			id: 'memory',
			label: 'Memory',
			description: 'Reuse saved facts and context',
			available: $config?.features?.enable_memories ?? false
		}
	];

	const toggleMemory = async () => {
		const nextMemory = !($settings?.memory ?? false);
		settings.set({ ...$settings, memory: nextMemory });
		await updateUserSettings(localStorage.token, { ui: { ...$settings, memory: nextMemory } }).catch(
			(error) => {
				console.error('Failed to update memory preference', error);
				settings.set({ ...$settings, memory: !nextMemory });
				toast.error($i18n.t('Failed to save settings'));
			}
		);
	};
</script>

<div
	class="rounded-[1.35rem] border border-gray-200/80 bg-white/90 text-left shadow-sm backdrop-blur-sm dark:border-gray-800 dark:bg-gray-900/80 {compact
		? 'px-3 py-2'
		: 'px-4 py-4'}"
>
	<div class="flex flex-wrap items-start justify-between gap-3">
		<div class="min-w-0 flex-1">
			<div class="flex flex-wrap items-center gap-2">
				<div class="rounded-full bg-gray-900 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-white dark:bg-gray-100 dark:text-gray-900">
					AI Workspace
				</div>

				{#if mode === 'auto' && route}
					<div class="rounded-full px-2 py-1 text-[11px] font-medium {confidenceClass(route.confidence)}">
						{route.confidence} confidence
					</div>
				{:else}
					<div class="rounded-full bg-gray-100 px-2 py-1 text-[11px] font-medium text-gray-600 dark:bg-gray-800 dark:text-gray-300">
						{mode === 'auto' ? 'Auto routing' : 'Manual routing'}
					</div>
				{/if}

				{#if canToggleMemory}
					<button
						type="button"
						class="rounded-full px-2 py-1 text-[11px] font-medium transition {featurePillClass(
							$settings?.memory ?? false
						)}"
						on:click={toggleMemory}
					>
						Memory {$settings?.memory ?? false ? 'on' : 'off'}
					</button>
				{/if}
			</div>

			<div class="mt-2 space-y-1">
				{#if route}
					<div class="text-sm font-semibold text-gray-900 dark:text-gray-100">
						{taskLabel(route.task)}{#if route.selected_model_name} with {route.selected_model_name}{/if}
					</div>
					<div class="text-xs text-gray-600 dark:text-gray-300">
						{route.workflow.join(' -> ')}
					</div>
				{:else if mode === 'manual'}
					<div class="text-sm font-semibold text-gray-900 dark:text-gray-100">
						Manual model selection
					</div>
					<div class="text-xs text-gray-600 dark:text-gray-300">
						Current model: {selectedModelSummary}
					</div>
				{:else}
					<div class="text-sm font-semibold text-gray-900 dark:text-gray-100">
						One chat window for text, voice, files, images and web tasks
					</div>
					<div class="text-xs text-gray-600 dark:text-gray-300">
						The workspace previews the task, picks the best model or tool, and keeps the conversation consistent.
					</div>
				{/if}
			</div>
		</div>
	</div>

	{#if route}
		<div class="mt-3 flex flex-wrap gap-2">
			{#each routeSources as source}
				<div class="rounded-full bg-gray-100 px-2.5 py-1 text-[11px] font-medium text-gray-600 dark:bg-gray-850 dark:text-gray-300">
					{source}
				</div>
			{/each}

			{#each enabledFeatures as [featureName, _enabled]}
				<div class="rounded-full bg-sky-100 px-2.5 py-1 text-[11px] font-medium text-sky-700 dark:bg-sky-950/70 dark:text-sky-200">
					{featureLabel(featureName)}
				</div>
			{/each}

			{#if route.memory_recommended && !($settings?.memory ?? false)}
				<div class="rounded-full bg-amber-100 px-2.5 py-1 text-[11px] font-medium text-amber-700 dark:bg-amber-950/70 dark:text-amber-200">
					Memory recommended
				</div>
			{/if}
		</div>

		{#if !compact && route.candidate_models?.length > 0}
			<div class="mt-3">
				<div class="text-[11px] font-medium uppercase tracking-[0.12em] text-gray-500 dark:text-gray-400">
					Candidate models
				</div>
				<div class="mt-2 flex flex-wrap gap-2">
					{#each route.candidate_models as candidate}
						<div class="rounded-2xl border border-gray-200 bg-gray-50 px-3 py-2 text-xs dark:border-gray-800 dark:bg-gray-850">
							<div class="font-medium text-gray-900 dark:text-gray-100">{candidate.name}</div>
							<div class="mt-0.5 text-gray-500 dark:text-gray-400">
								score {candidate.score}
								{#if candidate.matched_capabilities.length > 0}
									| {candidate.matched_capabilities.join(', ')}
								{/if}
							</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}
	{/if}

	{#if showCapabilities}
		<div class="mt-3 grid grid-cols-2 gap-2 lg:grid-cols-3">
			{#each capabilityCards as capability}
				<div
					class="rounded-2xl border px-3 py-3 transition {capability.available
						? 'border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900/60'
						: 'border-gray-100 bg-gray-50 text-gray-400 dark:border-gray-850 dark:bg-gray-900/40 dark:text-gray-500'}"
				>
					<div class="text-sm font-medium">{capability.label}</div>
					<div class="mt-1 text-xs">{capability.description}</div>
				</div>
			{/each}
		</div>
	{/if}
</div>
