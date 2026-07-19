import 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    requiresAuth?: boolean
    adminOnly?: boolean
    permission?: string
    icon?: string
  }
}
