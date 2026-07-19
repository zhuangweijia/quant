import { ref, onUnmounted, readonly } from "vue";
import { wsClient } from "@/utils/websocket";

export function useWebSocket() {
  const isConnected = ref(false);
  const channels = ref<string[]>([]);

  function onOpen() {
    isConnected.value = true;
    if (channels.value.length > 0) {
      wsClient.send({ action: "subscribe", channels: [...channels.value] });
    }
  }

  function onClose() {
    isConnected.value = false;
  }

  wsClient.on("connection:open", onOpen);
  wsClient.on("connection:close", onClose);

  function subscribe(...ch: string[]) {
    const newChannels = ch.filter((c) => !channels.value.includes(c));
    if (newChannels.length > 0) {
      channels.value.push(...newChannels);
      try {
        wsClient.send({ action: "subscribe", channels: newChannels });
      } catch (caught) {
        channels.value = channels.value.filter((channel) => !newChannels.includes(channel));
        throw caught;
      }
    }
  }

  function unsubscribe(...ch: string[]) {
    channels.value = channels.value.filter((c) => !ch.includes(c));
    wsClient.send({ action: "unsubscribe", channels: ch });
  }

  function onMessage(type: string, handler: (data: any) => void) {
    wsClient.on(type, handler);
    return () => wsClient.off(type, handler);
  }

  onUnmounted(() => {
    wsClient.off("connection:open", onOpen);
    wsClient.off("connection:close", onClose);
  });

  return {
    isConnected: readonly(isConnected),
    channels: readonly(channels),
    subscribe,
    unsubscribe,
    onMessage,
  };
}
