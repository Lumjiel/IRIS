import { createRouter, createWebHistory } from "vue-router";
import ChatView from "../views/ChatView.vue";

const routes = [
  { path: "/", name: "chat", component: ChatView },
  {
    path: "/settings",
    name: "settings",
    component: () => import("../views/SettingsView.vue"),
  },
  {
    path: "/history",
    name: "history",
    component: () => import("../views/HistoryView.vue"),
  },
  { path: "/:pathMatch(.*)*", redirect: "/" },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
