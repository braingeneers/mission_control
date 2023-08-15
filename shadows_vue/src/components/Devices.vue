<script>
    // import axios from 'axios'
    
    export default {
      props: ['type', 'interaction_things'],
      data () {
        return {
        //   interaction_things: [],
          error: null,
          user: [],
        }
      },
      methods:{
        redirectToURL(device_name){
          this.$router.push({ path: '/plates/'+device_name });
        },
        redirectToURL_wells(plate_name){
          this.$router.push({ path: '/wells/'+plate_name });
        },
    
      },
    //   async mounted () {
    //     try {
    //       console.log(this.type)
    //       const response = await axios.get(`${process.env.VUE_APP_API_ENDPOINT}/api/interaction-things?populate=%2A`)
    //       this.interaction_things = response.data.data
    //     } catch (error) {
    //       console.log(error)
    //       this.error = error;
    //     }
    //   }
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
        <div v-if="interaction_things.length">
            <div v-bind:key="device.id" v-for="device in interaction_things">
                <div v-if="type === device.attributes.type">
                    <b-card>

                        <div class="text-left">
                            <h4 class="text-properties">{{device.attributes.name}}  </h4>
        
                            <!-- horizontal white space -->
        
                            <b-card-text class="text-properties text-center"> Last updated: {{device.attributes.updatedAt | luxon}}</b-card-text>
                            <b-button class="float-right" v-b-toggle="'collapse-' + device.id" variant="primary">...</b-button>
                        </div>
                        <b-collapse v-bind:id="'collapse-' + device.id" class="mt-2">
                            <div>
                                <b-card-group>
                                    <b-card title="Type">
                                        <b-card-text class="text-left">
                                            {{device.attributes.type}}
                                        </b-card-text>
                                        <!-- <div v-bind:key="interaction_thing.id" v-for="interaction_thing in device.attributes.interaction_things.data">
                                                <b-button v-on:click="redirectToURL_wells(interaction_thing.attributes.name)">{{interaction_thing.attributes.name}}</b-button>
                                        </div> -->
                                        <template #footer>
                                            <small class="text-muted">footer</small>
                                        </template>
                                    </b-card>
        
                                    <b-card title="device-Notes">
                                        <b-card-text class="text-left">
                                            {{device.attributes.description}}
                                        </b-card-text>
                                        <template #footer>
                                            <small class="text-muted">Last updated 3 mins ago</small>
                                        </template>
                                    </b-card>
        
                                    <b-card title="Plates">
                                        <b-card-text>
                                            This is where we list plates
                                        </b-card-text>
                                            <!-- <div v-bind:key="plate.id" v-for="plate in device.attributes.plates.data"> -->
                                            <div v-if="device.attributes.current_plate.data">
                                                <b-button v-on:click="redirectToURL_wells(device.attributes.current_plate.data.attributes.name)">{{device.attributes.current_plate.data.attributes.name}}</b-button>
                                            </div>
                                        <template #footer>
                                            <small class="text-muted">Last updated 3 mins ago</small>
                                        </template>
                                    </b-card>
                                </b-card-group>
                            </div>
                        </b-collapse> 
                    </b-card>
                </div>

            </div>
        </div>
        <div v-else>
          <h5>Fetching devices . . .</h5>
        </div>
      </b-container>
    </template>
    