<template>
  <div class="experiments">
    <!-- <img alt="Vue logo" src="../assets/logo.png"> -->
    <Navbar />
    <Experiments />
  </div>
</template>

<script>
// @ is an alias to /src
// import HelloWorld from '@/components/HelloWorld.vue'
import Navbar from '@/components/Navbar.vue'
import Experiments from '@/components/Experiments.vue'

export default {
  name: 'ExperimentsView',
  components: {
    Navbar,
    Experiments,
 },
 methods:{

 },

}
</script>
