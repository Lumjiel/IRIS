import { ref } from "vue";

/**
 * Toast 全局提示 composable
 * 替代 App.vue 中的 toastMessage/toastType 局部状态
 */
export function useToast(duration = 2200) {
  const message = ref("");
  const type = ref("success");
  const visible = ref(false);
  let timer = null;

  const show = (msg, t = "success") => {
    message.value = msg;
    type.value = t;
    visible.value = true;
    clearTimeout(timer);
    timer = setTimeout(() => {
      visible.value = false;
    }, duration);
  };

  const success = (msg) => show(msg, "success");
  const error = (msg) => show(msg, "error");
  const info = (msg) => show(msg, "info");

  return { message, type, visible, show, success, error, info };
}
