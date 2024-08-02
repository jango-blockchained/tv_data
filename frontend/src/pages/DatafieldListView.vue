<!-- DatafieldListView.vue -->
<template>
    <div class="p-4">
        <h1 class="text-2xl font-bold mb-4">Datafield List</h1>
        <div v-if="isLoading" class="text-center">
            Loading...
        </div>
        <div v-else-if="error" class="text-red-500 p-4 bg-red-100 rounded">
            <p class="font-bold">Error:</p>
            <p v-if="error.includes('Keine Berechtigung') || error.includes('PermissionError')">
                You don't have permission to view the Datafield list. Please contact your administrator to request
                access.
            </p>
            <p v-else>
                An unexpected error occurred. Please try again later or contact support.
            </p>
            <button @click="refreshList" class="mt-4 bg-blue-500 text-white px-4 py-2 rounded">
                Refresh List
            </button>
        </div>
        <div v-else-if="datafields.length === 0" class="text-center">
            No Datafields found.
        </div>
        <div v-else class="overflow-x-auto">
            <table class="min-w-full bg-white">
                <thead class="bg-gray-100">
                    <tr>
                        <th class="py-2 px-4 text-left">Key</th>
                        <th class="py-2 px-4 text-left">Value</th>
                        <th class="py-2 px-4 text-left">User</th>
                        <th class="py-2 px-4 text-left">Type</th>
                        <th class="py-2 px-4 text-left">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="row in datafields" :key="row.name" class="border-b">
                        <td class="py-2 px-4">{{ row.key }}</td>
                        <td class="py-2 px-4">{{ row.value }}</td>
                        <td class="py-2 px-4">{{ row.user }}</td>
                        <td class="py-2 px-4">{{ row.type }}</td>
                        <td class="py-2 px-4">
                            <button @click="viewDetails(row.name)"
                                class="bg-blue-500 text-white px-2 py-1 rounded mr-2">
                                View
                            </button>
                            <button @click="extendSeries(row.name)" class="bg-green-500 text-white px-2 py-1 rounded">
                                Extend Series
                            </button>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</template>

<script>
import { ref, computed } from 'vue'
import { createResource } from 'frappe-ui'

export default {
    setup() {
        const listResource = createResource({
            url: 'tv_data.tv_data.doctype.datafield.datafield.get_list',
            params: {},
            auto: true,
        })

        const isLoading = computed(() => listResource.loading)
        const error = computed(() => listResource.error)
        const datafields = computed(() => listResource.data || [])

        const refreshList = () => {
            listResource.reload()
        }

        const viewDetails = (name) => {
            // Implement view details functionality
            console.log('View details for:', name)
        }

        const extendSeries = async (name) => {
            try {
                await createResource({
                    url: 'tv_data.tv_data.doctype.datafield.datafield.extend_series',
                    params: { doc_name: name },
                }).submit()

                // Reload the list after extending the series
                refreshList()
            } catch (error) {
                console.error('Error extending series:', error)
            }
        }

        return {
            isLoading,
            error,
            datafields,
            refreshList,
            viewDetails,
            extendSeries,
        }
    },
}
</script>