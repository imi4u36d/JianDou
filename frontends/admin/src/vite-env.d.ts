/// <reference types="vite/client" />

declare module "vue-router" {
  interface RouteMeta {
    title?: string;
    guestOnly?: boolean;
    requiresAdmin?: boolean;
  }
}

export {};
