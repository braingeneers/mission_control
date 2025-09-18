<script>
import axios from 'axios'

export default {
  data () {
    return {
      experiments: [],
      error: null,
      user: []
    }
  },
  methods:{
    redirectToURL(experiment_name){
      this.$router.push({ path: '/plates/'+experiment_name });
    },
    redirectToURL_wells(plate_name){
      this.$router.push({ path: '/wells/'+plate_name });
    },

  },
  async mounted () {
    try {
      var token = window.localStorage.getItem('jwt');
    //   console.log("is authenticated?", this.$auth.isAuthenticated)
      //if (!token){
      //  this.$router.push("/");
      //}
      const response = await axios.get(`https://shadows-db.braingeneers.gi.ucsc.edu/api/experiments?populate=%2A`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })
      this.experiments = response.data.data
    } catch (error) {
      this.error = error;
    }
  }
}
</script>
<style>
    .text-properties{
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
                    <h4 class="text-properties">{{experiment.attributes.name}}  </h4>

                    <!-- horizontal white space -->

                    <b-card-text class="text-properties text-center"> {{experiment.attributes.updatedAt | luxon}}</b-card-text>
                    <b-button class="float-right" v-b-toggle="'collapse-' + experiment.id" variant="primary">...</b-button>
                </div>
                <b-collapse v-bind:id="'collapse-' + experiment.id" class="mt-2">
                    <div>
                        <b-card-group>
                            <!-- <b-card title="Interaction-Things">
                            <b-card-text>
                                This is where we list interaction things
                            </b-card-text>
                            <div v-bind:key="interaction_thing.id" v-for="interaction_thing in experiment.attributes.interaction_things.data">
                                    <b-button v-on:click="redirectToURL_wells(interaction_thing.attributes.name)">{{interaction_thing.attributes.name}}</b-button>
                            </div>
                            <template #footer>
                                <small class="text-muted">footer</small>
                            </template>
                            </b-card> -->

                            <b-card title="Experiment-Notes">
                            <b-card-text class="text-left">
                                {{experiment.attributes.description}}
                            </b-card-text>
                            <template #footer>
                                <small class="text-muted">Last updated 3 mins ago</small>
                            </template>
                            </b-card>

                            <b-card title="Plates">
                            <b-card-text>
                                This is where we list plates
                            </b-card-text>
                                <div v-bind:key="plate.id" v-for="plate in experiment.attributes.plates.data">
                                    <b-button v-on:click="redirectToURL_wells(plate.attributes.name)">{{plate.attributes.name}}</b-button>
                                </div>
                            <template #footer>
                                <small class="text-muted">Last updated 3 mins ago</small>
                            </template>
                            </b-card>
                        </b-card-group>
                    </div>
                </b-collapse> 
                <!-- <span> -->
                    <!-- <div v-bind:key="well.id" v-for="well in experiment.attributes.wells.data">
                    <strong>{{ `${well.attributes.name}` }}</strong>
                    </div> -->
                <!-- </span> -->
                <!-- <button v-on:click="redirectToURL(experiment.attributes.name)"> Plates </button> -->
                <!-- <router-link to="/wells/" + ${experiment.attributes.name} >Wells</router-link>  -->

                <!-- removed bits
                v-bind:title="experiment.attributes.name"
             -->
                </b-card>
            <!-- </b-row> -->
        </div>
      <!-- </b-row> -->
    </div>
    <div v-else>
      <h5>Fetching experiments . . .</h5>
    </div>
  </b-container>
</template>
