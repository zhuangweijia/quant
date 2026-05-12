<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { strategyApi } from "@/api/strategy";
import { ElMessage } from "element-plus";
import { MARKET_LABELS } from "@/utils/constants";

const route = useRoute();
const router = useRouter();
const isEdit = computed(() => !!route.params.id);
const loading = ref(false);

const form = ref({
  name: "",
  description: "",
  code: `from app.core.types import BaseStrategy, BarData

class MyStrategy(BaseStrategy):
    def on_init(self, context):
        self.short_period = self.params.get("short_period", 5)
        self.long_period = self.params.get("long_period", 20)

    def on_bar(self, bar: BarData):
        bars = self.get_bars(bar.symbol, self.long_period + 1)
        if len(bars) < self.long_period:
            return
        # TODO: implement strategy logic
`,
  params: '{"short_period": 5, "long_period": 20}',
  market: "crypto",
});

onMounted(async () => {
  if (isEdit.value) {
    loading.value = true;
    try {
      const res: any = await strategyApi.get(route.params.id as string);
      const s = res.data;
      form.value = {
        name: s.name,
        description: s.description || "",
        code: s.code,
        params: s.params ? JSON.stringify(s.params, null, 2) : "{}",
        market: s.market,
      };
    } catch (e: any) {
      ElMessage.error("策略加载失败");
      router.push("/strategy");
    } finally {
      loading.value = false;
    }
  }
});

async function handleSave() {
  if (!form.value.name) {
    ElMessage.warning("请输入策略名称");
    return;
  }
  loading.value = true;
  try {
    let params = {};
    try {
      params = JSON.parse(form.value.params || "{}");
    } catch {
      ElMessage.error("策略参数 JSON 格式错误");
      loading.value = false;
      return;
    }

    const data = {
      name: form.value.name,
      description: form.value.description || undefined,
      code: form.value.code,
      params,
      market: form.value.market,
    };

    if (isEdit.value) {
      await strategyApi.update(route.params.id as string, data);
      ElMessage.success("策略已更新");
    } else {
      await strategyApi.create(data);
      ElMessage.success("策略已创建");
    }
    router.push("/strategy");
  } catch (e: any) {
    ElMessage.error(e.message || "保存失败");
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div>
    <el-card shadow="hover">
      <template #header>
        <span>{{ isEdit ? "编辑策略" : "创建策略" }}</span>
      </template>

      <el-form :model="form" label-width="100px" v-loading="loading" style="max-width: 900px">
        <el-form-item label="策略名称">
          <el-input v-model="form.name" placeholder="输入策略名称" />
        </el-form-item>
        <el-form-item label="目标市场">
          <el-select v-model="form.market">
            <el-option
              v-for="(label, value) in MARKET_LABELS"
              :key="value"
              :label="label"
              :value="value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="策略描述（可选）" />
        </el-form-item>
        <el-form-item label="策略代码">
          <el-input
            v-model="form.code"
            type="textarea"
            :rows="20"
            font="monospace"
            style="font-family: 'Courier New', monospace"
          />
        </el-form-item>
        <el-form-item label="策略参数">
          <el-input
            v-model="form.params"
            type="textarea"
            :rows="6"
            style="font-family: 'Courier New', monospace"
            placeholder="JSON 格式"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSave" :loading="loading">
            {{ isEdit ? "更新策略" : "创建策略" }}
          </el-button>
          <el-button @click="router.push('/strategy')">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>
