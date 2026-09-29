import type { RouteRecordRaw } from 'vue-router'
export const qaReportRoutes: RouteRecordRaw[] = [
  {
    path: '/qa-reports',
    component: () => import('./views/HistoryView.vue'),
    meta: { title: 'Daftar laporan QA' },
  },
  {
    path: '/qa-reports/new',
    component: () => import('./views/ReportView.vue'),
    meta: { title: 'Laporan baru', newReport: true },
  },
  {
    path: '/qa-reports/history',
    redirect: '/qa-reports',
  },
  {
    path: '/qa-reports/templates',
    component: () => import('./views/TemplatesView.vue'),
    meta: { title: 'Template laporan QA' },
  },
  {
    path: '/qa-reports/templates/new',
    component: () => import('./views/TemplateEditorView.vue'),
    meta: { title: 'Template laporan baru' },
  },
  {
    path: '/qa-reports/templates/:templateId/edit',
    component: () => import('./views/TemplateEditorView.vue'),
    meta: { title: 'Edit template laporan' },
  },
  {
    path: '/qa-reports/monthly',
    component: () => import('./views/MonthlyView.vue'),
    meta: { title: 'Ringkasan bulanan' },
  },
  {
    path: '/qa-reports/:id',
    component: () => import('./views/ReportView.vue'),
    meta: { title: 'Laporan harian' },
  },
]
