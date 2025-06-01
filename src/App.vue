<template>
    <div id="app" style="height: 100%;">
        <router-view/>
        <HelpBox />
    </div>
</template>

<script>
import HelpBox from './components/HelpBox.vue'

export default {
    name: 'App',
    components: {
        HelpBox
    }
}
</script>

<style>

@import url('https://fonts.googleapis.com/css?family=Nunito+Sans&display=swap');

 #app {
    font-family: 'Nunito Sans', sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
 }

 html,
body {
    overscroll-behavior-y: contain;
}

</style>