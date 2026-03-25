<template>
  <div class="mx-auto flex min-h-screen max-w-7xl flex-col px-4 py-6 sm:px-6 lg:px-8">
    <header class="mb-8 flex flex-col gap-4 rounded-[28px] border border-white/10 bg-white/5 p-5 shadow-panel backdrop-blur">
      <div class="flex items-center justify-between gap-4">
        <div>
          <p class="text-xs uppercase tracking-[0.35em] text-orange-300">AI Drama Clip Studio</p>
          <h1 class="mt-2 text-3xl font-semibold tracking-tight text-white">AI Cut</h1>
        </div>
        <nav class="flex gap-2">
          <RouterLink to="/tasks" class="rounded-full border border-white/10 px-4 py-2 text-sm text-slate-200 transition hover:border-orange-300 hover:text-white">任务列表</RouterLink>
          <RouterLink to="/tasks/new" class="rounded-full bg-orange-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-orange-400">新建任务</RouterLink>
        </nav>
      </div>
      <p class="max-w-3xl text-sm leading-6 text-slate-300">
        上传原始视频，配置时长范围、产出数量、片头片尾模板和平台方向，系统会自动生成可预览的短剧投放素材。
      </p>
    </header>
    <main class="flex-1">
      <RouterView />
    </main>
  </div>
</template>

