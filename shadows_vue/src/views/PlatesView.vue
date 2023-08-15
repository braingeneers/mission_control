<template>
  <div class="home">
    <!-- <img alt="Vue logo" src="../assets/logo.png"> -->
    <Navbar />
    <!-- <DirectionalPad /> -->
    <Plates ref="plates" v-bind:experiment_name="experiment_name_from_url"/>
  </div>
</template>

<script>
// @ is an alias to /src
// import HelloWorld from '@/components/HelloWorld.vue'
import Navbar from '@/components/Navbar.vue'
import Plates from '@/components/Plates.vue'
// import DirectionalPad from '@/components/DirectionalPad.vue'


export default {
  name: 'PlatesView',
  props: ['experiment_name_from_url'],
  components: {
    Navbar,
    Plates,
    // DirectionalPad,
}
}
</script>
