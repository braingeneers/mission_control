<template>
    <div class="devices">
        <!-- <img alt="Vue logo" src="../assets/logo.png"> -->
        <Navbar />
        <div ref="BioPlateScopes">
            <!-- <h4>BioPlateScopes</h4> -->
            <b-button pill  v-b-toggle="'collapse-scopes'"
                variant="primary"> BioPlateScopes </b-button>
            <b-collapse v-bind:id="'collapse-scopes'" class="mt-2">
                <Devices v-bind:type="'BioPlateScope'" v-bind:interaction_things="interaction_things" />
            </b-collapse>
        </div>
        <div ref="Autoculture">
            <b-button pill  v-b-toggle="'collapse-Autoculture'"
                variant="primary"> Autoculture </b-button>
            <b-collapse v-bind:id="'collapse-Autoculture'" class="mt-2">
                <Devices v-bind:type="'Autoculture'" v-bind:interaction_things="interaction_things" />
            </b-collapse>
        </div>
        <div ref="Maxwell">
            <h4>Maxwell</h4>
            <Devices v-bind:type="'Maxwell'" v-bind:interaction_things="interaction_things" />
        </div>
        <div ref="Other">
            <h4>Other</h4>
            <Devices v-bind:type="'Other'" v-bind:interaction_things="interaction_things" />
        </div>

    </div>
</template>
  
<script>
// @ is an alias to /src
// import HelloWorld from '@/components/HelloWorld.vue'
import axios from 'axios'
import Navbar from '@/components/Navbar.vue'
import Devices from '@/components/Devices.vue'

export default {
    name: 'DevicesView',
    components: {
        Navbar,
        Devices,
    },
    data() {
        return {
            interaction_things: [],
            error: null,
            user: [],
        }
    },
    async mounted() {
        try {
            const response = await axios.get(`https://shadows-db.braingeneers.gi.ucsc.edu/api/interaction-things?populate=%2A`, {
                headers: {
                    Authorization: `Bearer ${window.localStorage.getItem('jwt')}`
                }
            });
            this.interaction_things = response.data.data
        } catch (error) {
            console.log(error)
            this.error = error;
        }
    }
}
</script>
  
