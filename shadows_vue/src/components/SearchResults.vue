<script>
import axios from 'axios'

export default {
    props: ['query'],
    data() {
        return {
            experiments: [],
            error: null,
            user: []
        }
    },
    methods: {
        redirectToURL(experiment_name) {
            this.$router.push({ path: '/plates/' + experiment_name });
        },
        redirectToURL_wells(plate_name) {
            this.$router.push({ path: '/wells/' + plate_name });
        },

    },
    async mounted() {
        try {
            var token = window.localStorage.getItem('jwt');
            //   console.log("is authenticated?", this.$auth.isAuthenticated)
            if (!token) {
                this.$router.push("/");
            }
            console.log(this.query)
            const response = await axios.get(`https://shadows-db.braingeneers.gi.ucsc.edu/api/fuzzy-search/search?query=${this.query}`, {
                headers: {
                    Authorization: `Bearer ${token}`
                }
            });
            this.experiments = response.data.experiments
            console.log(JSON.stringify(this.experiments))
        } catch (error) {
            this.error = error;
        }
    }
}
</script>
<style>
.text-properties {
    display: inline;
    min-width: 2000px;
}
</style>
    
    
<template>
    <b-container>

        <div v-if="experiments.length">
            <!-- <b-row> -->
            <div v-bind:key="experiment.id" v-for="experiment in experiments">
                <!-- <b-row> -->
                <b-card>

                    <div class="text-left">
                        <h4 class="text-properties">{{ experiment.name }} </h4>

                        <!-- horizontal white space -->

                        <b-card-text class="text-properties text-center"> {{ experiment.updatedAt | luxon }}</b-card-text>
                        <b-button class="float-right" v-b-toggle="'collapse-' + experiment.id" variant="primary">...
                        </b-button>
                    </div>
                    <b-collapse v-bind:id="'collapse-' + experiment.id" class="mt-2">
                        <div>
                            <b-card-group>
                                <!-- <b-card title="Interaction-Things">
                                <b-card-text>
                                    This is where we list interaction things
                                </b-card-text>
                                <div v-bind:key="interaction_thing.id" v-for="interaction_thing in experiment.interaction_things.data">
                                        <b-button v-on:click="redirectToURL_wells(interaction_thing.name)">{{interaction_thing.name}}</b-button>
                                </div>
                                <template #footer>
                                    <small class="text-muted">footer</small>
                                </template>
                                </b-card> -->

                                <b-card title="Experiment-Notes">
                                    <b-card-text class="text-left">
                                        {{ experiment.description }}
                                    </b-card-text>
                                    <template #footer>
                                        <small class="text-muted">Last updated 3 mins ago</small>
                                    </template>
                                </b-card>

                                <b-card title="Plates">
                                    <b-card-text>
                                        This is where we list plates
                                    </b-card-text>
                                    <!-- <div v-bind:key="plate.id" v-for="plate in experiment.plates.data">
                                        <b-button v-on:click="redirectToURL_wells(plate.name)">{{plate.name}}</b-button>
                                    </div> -->
                                    <template #footer>
                                        <small class="text-muted">Last updated 3 mins ago</small>
                                    </template>
                                </b-card>
                            </b-card-group>
                        </div>
                    </b-collapse>
                    <!-- <span> -->
                    <!-- <div v-bind:key="well.id" v-for="well in experiment.wells.data">
                        <strong>{{ `${well.name}` }}</strong>
                        </div> -->
                    <!-- </span> -->
                    <!-- <button v-on:click="redirectToURL(experiment.name)"> Plates </button> -->
                    <!-- <router-link to="/wells/" + ${experiment.name} >Wells</router-link>  -->

                    <!-- removed bits
                    v-bind:title="experiment.name"
                 -->
                </b-card>
                <!-- </b-row> -->
            </div>
            <!-- </b-row> -->
        </div>
        <div v-else>
            <h5>No results found . . .</h5>
        </div>
    </b-container>
</template>
    
