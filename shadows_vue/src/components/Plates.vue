<script>
import axios from 'axios'

export default {
  props: ["experiment_name"],
  data () {
    return {
      plates: [],
      filter_params: "?filters[experiments][name][$contains]=",
      error: null
    }
  },
  methods:{
    redirectToURL(plate_name){
      this.$router.push({ path: '/wells/'+plate_name });
    },
  },
//   async mounted () {
//     try {
//       const response = await axios.get('${process.env.VUE_APP_API_ENDPOINT}/api/plates?populate=%2A')
//       this.plates = response.data.data
//     } catch (error) {
//       this.error = error;
//     }
//   }
    async mounted() {
        var token = window.localStorage.getItem('jwt');
        if (!token){
            this.$router.push("/");
        }
        try {
            console.log(this.filter_params)
            console.log(this.experiment_name)
            if (!this.experiment_name) {
                this.filter_params = ""
            } else {
                this.filter_params = this.filter_params + this.experiment_name
            }
            // ${this.plate_name}
            const response = await axios.get(`${process.env.VUE_APP_API_ENDPOINT}/api/plates${this.filter_params}`)

            this.plates = response.data.data
        } catch (error) {
            this.error = error;
        }
    },
}
</script>


<template>
    <b-container>
    <div v-if="plates.length">
      <b-row>
        <div v-bind:key="plate.id" v-for="plate in plates">
          <b-col l="4">
            <b-card
              v-bind:img-src="`https://via.placeholder.com/150`"
              v-bind:title="plate.attributes.name"
              img-alt="Image"
              img-top
              tag="article"
              style="max-width: 20rem;"
              class="mb-2"
            >
              <b-card-text>{{` ${plate.attributes.description}` }}</b-card-text>
              <span>
                <!-- <div v-bind:key="well.id" v-for="well in plate.attributes.wells.data">
                  <strong>{{ `${well.attributes.name}` }}</strong>
                </div> -->
              </span>
              <button v-on:click="redirectToURL(plate.attributes.name)"> Wells </button>
              <!-- <router-link to="/wells/" + ${plate.attributes.name} >Wells</router-link>  -->
            </b-card>
          </b-col>
        </div>
      </b-row>
    </div>
    <div v-else>
      <h5>Fetching plates . . .</h5>
    </div>
  </b-container>
</template>
