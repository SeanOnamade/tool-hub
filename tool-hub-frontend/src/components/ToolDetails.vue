<template>
    <div class="p-6 max-w-4xl mx-auto">
        <button @click = "$router.go(-1)" class = "text-blue-500 underline mb-4">Back</button>
    <div v-if = "tool">
        <h1 class = "text-3xl font-bold mb-2">{{  tool.name }}</h1>
        <p class = "mb-4">{{  tool.description }}</p>
        <p class = "mb-4">Category: {{  tool.category }}</p>
        <a :href = "tool.url" target="_blank" class = "text-blue-600 hover: underline"> Visit Tool </a>
    </div>
    <div v-else>
        <p>Loading tool details...</p>
    </div>
    </div>
</template>

<script>
import axios from "axios";

export default {
    data() {
        return {
            tool: null,
        };
    },
    created() {
        const toolId = this.$route.params.id;
        axios
            .get(`http://localhost:8000/tools/${toolId}`)
            .then((response) => {
                this.tool = response.data;
            })
            .catch((error) => {
                console.error("Errror fetching tool details:", error);
            });
    },
};
</script>