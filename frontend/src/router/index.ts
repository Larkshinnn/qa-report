import { createRouter, createWebHistory } from 'vue-router'
import { qaReportRoutes } from '../modules/qa-reports/routes'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/qa-reports' },
    ...qaReportRoutes,
    {
      path: '/:pathMatch(.*)*',
      component: () => import('../shared/views/NotFoundView.vue'),
      meta: { title: 'Halaman tidak ditemukan' },
    },
  ],
  scrollBehavior: () => ({ top: 0 }),
})
router.afterEach((to) => {
  document.title = `${String(to.meta.title ?? 'QA Report')} · QA Report`
})
