<script>
import axios from 'axios'
import $ from 'jquery'
import { Annotorious } from '@recogito/annotorious';
import '@recogito/annotorious/dist/annotorious.min.css';
import SelectorPack from '@recogito/annotorious-selector-pack';
// import '@recogito/annotorious-selector-pack/dist/annotorious-selector-pack.min.css';

import DirectionalPad from '@/components/DirectionalPad.vue'

export default {
    props: ["plate_name"],
    components: {
        DirectionalPad,
    },
    data() {
        return {
            plate: { "attributes": { "image_parameters": false } },
            wells: [],
            //   filter_string: '?filters[plate][name][$eq]=test-plate-1',
            filter_params: "?filters[plate][name][$contains]=",
            error: null,
            form: {
                sample_name: '',
                sample_description: ''
            },
            rows: 0,
            columns: 0,
            //image viewer stuff
            progress: 0,
            images: [],
            uuid: "",
            groupID: "",
            endpoint: `${process.env.VUE_APP_S3_ENDPOINT}/braingeneers/imaging`,
            manifest: {
                stack_size: 0,
                captures: [],
            },
            curTimestampIndex: 0,
            curZ: 0,
            curRow: 1,
            curCol: 1,
            firstLoadIndex: 0,
            startTimestampIndex: 0,
            startZ: 0,
            panning: false,
            timers: [],
            anno: null,
            curWell_id: null,
        }

    },
    async mounted() {
        try {
            var token = window.localStorage.getItem('jwt');
            //   console.log("is authenticated?", this.$auth.isAuthenticated)
            if (!token){
                this.$router.push("/");
            }
            // console.log(process.env.VUE_APP_API_ENDPOINT)
            // console.log("endpoint",  this.endpoint)
            // console.log(process.env.VUE_APP_S3_ENDPOINT)
            // console.log(this.filter_params)
            // console.log(this.plate_name)
            if (!this.plate_name) {
                this.filter_params = ""
            } else {
                this.filter_params = this.filter_params + this.plate_name
            }
            // ${this.plate_name}
            //added populate=* to get all the associated nested data
            const response = await axios.get(`${process.env.VUE_APP_API_ENDPOINT}/api/wells${this.filter_params}&populate=*`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })
            this.wells = response.data.data
            await axios.get(`${process.env.VUE_APP_API_ENDPOINT}/api/plates?filters[name][$eq]=${this.plate_name}`, { 
                headers: {
                    'Authorization': `Bearer ${token}`
                }
                }).then((response) => {
                this.plate = response.data.data[0]
                this.rows = this.plate.attributes.rows
                this.columns = this.plate.attributes.columns
                if (this.hasImages()) {

                    console.log("first load uuid:", Object.keys(this.plate.attributes.image_parameters.uuids)[0])
                    this.uuid = Object.keys(this.plate.attributes.image_parameters.uuids)[0]
                    this.groupID = this.plate.attributes.image_parameters.uuids[this.uuid]
                    this.loader("oldest")
                }
            })
            // this.plate = response2.data.data[0]
            // // console.log("plate", JSON.stringify(this.plate.attributes.image_parameters.images, 0, 2))
            // this.rows = this.plate.attributes.rows
            // this.columns = this.plate.attributes.columns
            // if (this.hasImages()) {
            //     this.uuid = this.plate.attributes.image_parameters.uuids
            //     // this.groupID = this.plate.attributes.image_parameters.group_id
            //     this.loader("oldest")
            // }
            // this.initAnno();
            // console.log("wells", JSON.stringify(this.wells, 0, 2))
            // console.log(this.wells)
        } catch (error) {
            console.log(error)
            this.error = error;
        }
    },
    methods: {
        hasImages() {
            // console.log("cond 1",Object.prototype.hasOwnProperty.call(this.plate.attributes.image_parameters, "uuids"))
            // console.log("cond 2", JSON.stringify(this.plate.attributes.image_parameters.uuids, 0, 2))
            // console.log("cond 3", this.plate.attributes.image_parameters["uuids"] != {})
            if (Object.prototype.hasOwnProperty.call(this.plate.attributes.image_parameters, "uuids") && this.plate.attributes.image_parameters["uuids"] != {}) {
                return true
            }
            return false
        },

        initAnno() {
            if (!this.anno) {
                this.anno = new Annotorious({
                    image: document.getElementById("well-image")
                });

                // this.anno.SelectorPack(this.anno)
                // new AnnotoriousSelectorPack(this.anno);
                console.log(JSON.stringify(this.anno.listDrawingTools(), 0, 2))
                console.log(SelectorPack(this.anno))
                console.log(JSON.stringify(this.anno.listDrawingTools(), 0, 2))

                this.anno.setDrawingTool("circle")
                // console.log(window.SelectorPack)
                // SelectorPack(this.anno)
                this.anno.on('createAnnotation', (annotation) => {
                    console.log('Created annotation', JSON.stringify(annotation));
                    this.createSample(this.curWell_id, annotation)
                });

                this.anno.on('createSelection', function (selection) {
                    console.log('Created selection', selection);
                });

                this.anno.on('deleteAnnotation', function (annotation) {
                    console.log('Delete annotation', annotation);
                });

                this.anno.on('mouseEnterAnnotation', function (annotation) {
                    console.log('Mouse ENTERED annotation', annotation);
                });

                this.anno.on('selectAnnotation', function (annotation) {
                    console.log('Select annotation', annotation);
                });

                this.anno.on('cancelSelected', function () {
                    console.log('UNSELECTED');
                });

                this.anno.on('clickAnnotation', function (annotation) {
                    console.log('Clicked annotation', annotation);
                });
            } else {
                console.log("anno already exists")
            }
        },
        loadAnno(annotation) {
            if (!this.anno) {
                this.initAnno();
                console.log("initted anno")
            }

            this.anno.addAnnotation(annotation);
            console.log("added annotation")
            console.log(JSON.stringify(annotation, 0, 2))
        },
        showModal(id) {
            //reset progress bar
            this.progress = 0
            console.log("#" + id)
            $("#" + id).click();
            // this.initAnno();
        },
        createSample(well_id, annotation) {
            console.log("create sample")
            // console.log(this.form.sample_name)
            // console.log(this.form.sample_description)
            console.log(well_id)
            // if (!(this.form.sample_name && this.form.sample_description) && annotation) {
            //     this.form.sample_name = annotation.body[0].value
            //     this.form.sample_description = annotation.body[0].value

            // }

            // post with jwt
            var token = window.localStorage.getItem('jwt');
            axios.post(`${process.env.VUE_APP_API_ENDPOINT}/api/samples`, {
                data: {
                    // name: this.form.sample_name,
                    name: annotation.body[0].value,
                    // description: this.form.sample_description,
                    well: well_id,
                    annotation: annotation
                }
            }, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })
                .then(response => {
                    console.log(JSON.stringify(response, 0, 2));
                    if (response.status == 200) {
                        //refresh the wells
                        axios.get(`${process.env.VUE_APP_API_ENDPOINT}/api/wells${this.filter_params}&populate=*`, { headers: { 'Authorization': `Bearer ${token}` } })
                            .then(response => {
                                // console.log(JSON.stringify(response, 0, 2));
                                this.wells = []
                                this.wells = response.data.data
                            })
                            .catch(function (error) {
                                console.log(error);
                            });
                    }
                })
                .catch(function (error) {
                    console.log(error);
                });
        },
        getSamples(well_id) {
            console.log("get samples")
            console.log(well_id)
            // post with api_token
            axios.get(`${process.env.VUE_APP_API_ENDPOINT}/api/samples?filters[well][id][$eq]=${well_id}`, { headers: { 'Authorization': `Bearer ${window.localStorage.getItem('jwt')}` } })
                .then(function (response) {
                    console.log(response);
                })
                .catch(function (error) {
                    console.log(error);
                });
        },
        deleteSample(sample) {
            console.log("delete sample")
            console.log(JSON.stringify(sample, 0, 2))
            // post with jwt token
            var token = window.localStorage.getItem('jwt');
            axios.delete(`${process.env.VUE_APP_API_ENDPOINT}/api/samples/${sample.id}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })
                .then(response => {
                    console.log(response);
                    if (response.status == 200) {
                        axios.get(`${process.env.VUE_APP_API_ENDPOINT}/api/wells${this.filter_params}&populate=*`, { headers: { 'Authorization': `Bearer ${token}` } })
                            .then(response => {
                                console.log(response);
                                this.wells = []
                                this.wells = response.data.data
                            })
                            .catch(function (error) {
                                console.log(error);
                            });
                    }
                })
                .catch(function (error) {
                    console.log(error);
                });

            if (sample.attributes.annotation) {
                console.log(sample.attributes.annotation.id)
                this.anno.removeAnnotation(sample.attributes.annotation.id)
            }
            // this.anno.addAnnotation(annotation);
            // console.log("added annotation")
            // console.log(JSON.stringify(annotation, 0, 2))
            // delete page element

            // console.log("deleting page element: " + "sample-" + sample_id);
            // $("#"+'sample-'+sample_id).remove();
        },
        // begin image viewer stuff
        loader(start_index) {
            console.log(start_index)
            console.log("Loading...", this.uuid)
            console.log(`${this.endpoint}/${this.uuid}/images/manifest.json`)
            fetch(`${this.endpoint}/${this.uuid}/images/manifest.json`)
                .then(stream => stream.json())
                .then(data => {
                    this.manifest = data
                    switch (start_index) {
                        case "newest":
                            this.curTimestampIndex = this.manifest.captures.length - 1
                            this.firstLoadIndex = this.manifest.captures.length - 1
                            break;
                        case "oldest":
                            this.curTimestampIndex = 0
                            this.firstLoadIndex = 0
                            break;
                        case "sync":
                            this.firstLoadIndex = this.curTimestampIndex
                            break;
                        default:
                        // console.log(this.loadTrigger)

                    }
                })
                .catch(error => {
                    console.log(error)
                    alert("Unable to load experiment, does the uuid exist?")
                })
        },
        changeImageSet(uuid, group_id) {
            this.uuid = uuid
            this.groupID = group_id
            this.loader("newest")
        },
        missing(event) {
            console.log("Missing image", event.target.src)
            event.target.src = "https://placekitten.com/g/560/420"
        },
        OnArrowRightClick() {
            console.log()
            if (this.curTimestampIndex < this.manifest.captures.length - 1) {
                this.curTimestampIndex = this.curTimestampIndex + 1
            }
            else {
                console.log("At max timestamp")
                console.log("this.curTimestampIndex: " + this.curTimestampIndex)
            }
        },
        OnArrow48RightClick() {
            console.log()
            if (this.curTimestampIndex < this.manifest.captures.length - 49) {
                this.curTimestampIndex = this.curTimestampIndex + 48
            }
            else {
                this.curTimestampIndex = this.manifest.captures.length - 1
                console.log("At max timestamp")
                console.log("this.curTimestampIndex: " + this.curTimestampIndex)
            }
        },
        OnArrowLeftClick() {
            console.log()
            if (this.curTimestampIndex > 0) {
                this.curTimestampIndex = this.curTimestampIndex - 1
            }
            else {
                console.log("At minimum timestamp")
                console.log("this.curTimestampIndex: " + this.curTimestampIndex)
            }
        },
        OnArrow48LeftClick() {
            console.log()
            if (this.curTimestampIndex > 48) {
                this.curTimestampIndex = this.curTimestampIndex - 48
            }
            else {
                this.curTimestampIndex = 0
                console.log("At first timestamp")
                console.log("this.curTimestampIndex: " + this.curTimestampIndex)
            }
        },
        OnPreviousFocalViewClick() {
            if (this.curZ > 0) {
                this.stopLoading()
                console.log("this.curZ: " + this.curZ)
                this.startZ = this.curZ
                this.curZ = this.startZ - 1

            } else {
                console.log("At minimum focal length")
            }
        },
        OnNextFocalViewClick() {
            if (this.curZ < this.manifest.stack_size - 1) {
                this.stopLoading()
                console.log("this.curZ: " + this.curZ)
                this.startZ = this.curZ
                this.curZ = this.startZ + 1

            } else {
                console.log("At maximum focal length")
            }
        },
        loadAllImagesFromLayer(row, col, layer) {
            console.log("load all images from layer", row, col, layer)
            // fetch image from url with axios
            // axios.get(`${process.env.VUE_APP_API_ENDPOINT}/api/wells${this.filter_params}&populate=*`)
            var length = this.manifest.captures.length
            var count = 0
            this.images = []
            var self = this
            self.progress = 0
            this.manifest.captures.forEach((capture, index) => {
                self.images.push(new Image())
                self.images[index].src = `${this.endpoint}/${this.uuid}/images/${capture}/camera${this.groupID}${row}${col}/${layer + 1}.jpg`
                self.images[index].onload = function () {
                    console.log("loaded image")

                    // .progress++
                    // console.log(self.progress)
                    count = count + 1
                    self.progress = (count / length) * 100
                }

                // ((count / length) * 100)

            })
        },
        stopLoading() {
            for (var i = 0; i < this.images.length; i++) {
                this.images[i].src = ""
            }
            this.images = []
            this.progress = 0
        },
        playTimelapse() {
            // this.break_timelapse = false
            var self = this
            // for (let i = 0; i < this.manifest.captures.length; i = i + 1){
            //     if (self.break_timelapse == true){
            //         break
            //     }
            //     setTimeout(function(){
            //         self.curTimestampIndex = i
            //     }, 10)
            // }
            this.manifest.captures.every((capture, index) => {
                self.timers.push(setTimeout(function () {
                    self.curTimestampIndex = index
                }, 75 * index))

                return true

            })
        },
        clearTimer() {
            this.timers.forEach(timer => {
                clearTimeout(timer)
            })
            this.timers = []
        },
    }
}
</script>

<style>
.img-wrap {
    width: auto;
    height: auto;
    position: relative;
    display: inline-block;
    overflow: hidden;
    margin: 0;

}

.img-card-fill {
    width: 100%;
    height: 100%;
    display: block;
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);

    /* min-height: 100%;
        min-width: 100%; */
}

.responsive {
    width: 100%;
    height: auto;
    /* padding-top: 5px;
        padding-right: 0;
        padding-left: 0; */
}

.column-padding {
    padding: 2.5px;
}

/* #my-button{
        height:0px;
        width:0px
    }  */
</style>


<template>
    <b-container fluid="xl">
        <!-- <img id="example" src="https://placekitten.com/g/560/420" /> -->
        <!-- display plate name header -->
        <b-row>
            <h1>Plate: {{plate_name}}</h1>
        </b-row>
        <div v-if="wells.length">
            <!-- <b-row> -->
            <!-- <table id="picture-grid"> -->
            <div v-for="row in rows" :key="row">
                <b-row>
                    <b-col class="column-padding" v-for="col in columns" :key="row * 10 + col">
                        <img class="responsive"
                            v-on:click="showModal('boof' + wells[((row-1)*columns+col)-1].id); curWell_id=wells[((row-1)*columns+col)-1].id"
                            @error="missing($event)"
                            :src="`${endpoint}/${uuid}/images/${manifest.captures[firstLoadIndex]}/camera${groupID}${row}${col}/${0 + 1}.jpg`" />
                        <div>
                            <!-- <b-button  id="indirect-button" @click="showModal('boof' + wells[((row-1)*columns+col)-1].id)" > indirect</b-button> -->
                            <b-button style="display:none" v-bind:id="'boof'+ wells[((row-1)*columns+col)-1].id"
                                v-b-modal="'modal-centere' + wells[((row-1)*columns+col)-1].id">Launch centered modal
                            </b-button>
                            <b-modal size="lg" v-bind:id="'modal-centere' + wells[((row-1)*columns+col)-1].id" centered
                                v-bind:title=wells[((row-1)*columns+col)-1].attributes.name>
                                <b-row>
                                    Current Timestamp: {{curTimestampIndex+1}}/{{manifest.captures.length}}
                                </b-row>
                                <!-- new line -->
                                <b-row>
                                    T: {{ manifest.captures[curTimestampIndex] | luxon}}
                                </b-row>
                                <b-row>
                                    Z: {{ curZ+1 }}/{{manifest.stack_size}}
                                </b-row>
                                <img id="well-image" class="responsive" @error="missing($event)"
                                    :src="`${endpoint}/${uuid}/images/${manifest.captures[curTimestampIndex]}/camera${groupID}${row}${col}/${curZ + 1}.jpg`">
                                <b-row>
                                    <b-col>
                                        <div class="p-1">
                                            <b-button class="btn btn-secondary btn-sm"
                                                v-on:click="loadAllImagesFromLayer(row, col, curZ)">
                                                Load all images for current layer
                                            </b-button>
                                            <vue-ellipse-progress class="float-right" :size="30" :progress="progress"
                                                animation="default 0 0" />
                                            <b-button class="btn btn-secondary btn-sm" v-on:click="stopLoading()">
                                                Stop Loading
                                            </b-button>
                                        </div>
                                        <div class="p-1">
                                            <b-row>
                                                <b-button style="padding: 5px" class="btn btn-secondary btn-sm"
                                                    @click="playTimelapse()">Play Timelapse</b-button>
                                                <b-button style="padding: 5px" class="btn btn-secondary btn-sm"
                                                    @click="clearTimer()">Stop Timelapse</b-button>
                                            </b-row>
                                        </div>
                                        <b-button pill style="display:block;"
                                            v-b-toggle="'collapse-samples-' + wells[((row-1)*columns+col)-1].id"
                                            variant="primary"> List Samples</b-button>
                                        <b-collapse v-bind:id="'collapse-samples-' + wells[((row-1)*columns+col)-1].id"
                                            class="mt-2">
                                            <b-list-group>
                                                <b-list-group-item
                                                    v-for="sample in wells[((row-1)*columns+col)-1].attributes.samples.data"
                                                    :key="sample.id">
                                                    <div v-bind:id="'sample-' +sample.id">
                                                        <b-button v-b-toggle="'collapse-sample' + sample.id"
                                                            @click="loadAnno(sample.attributes.annotation)"
                                                            variant="secondary"> {{sample.attributes.name}} </b-button>
                                                        <b-button v-on:click="deleteSample(sample)" class="float-right"
                                                            v-bind:id="'delete-sample-'+sample.id" variant="danger"> X
                                                        </b-button>
                                                        <b-collapse v-bind:id="'collapse-sample' + sample.id"
                                                            class="mt-2">
                                                            <b-card>
                                                                <!-- <b-card-text>{{sample.attributes.description}} -->
                                                                <b-card-text>
                                                                    {{JSON.stringify(sample.attributes.annotation)}}
                                                                </b-card-text>
                                                            </b-card>
                                                        </b-collapse>
                                                    </div>
                                                </b-list-group-item>

                                            </b-list-group>
                                        </b-collapse>
                                        <b-button pill style="display:block;" @click="initAnno();"
                                            v-b-toggle="'collapse-create-sample-' + wells[((row-1)*columns+col)-1].id"
                                            variant="success"> Label new sample</b-button>
                                        <b-collapse
                                            v-bind:id="'collapse-create-sample-' + wells[((row-1)*columns+col)-1].id"
                                            class="mt-2">
                                            <div>
                                                <!-- button and text field to add sample to the database via restAPI call -->
                                                <!-- <b-form
                                                    @submit.prevent="createSample(wells[((row-1)*columns+col)-1].id)">
                                                    <b-form-group id="input-group-1" label="Sample Name:"
                                                        label-for="input-1" description="name the sample">
                                                        <b-form-input id="input-1" v-model="form.sample_name"
                                                            placeholder="name" required></b-form-input>
                                                    </b-form-group>
                                                    <b-form-group id="input-group-2" label="Description:"
                                                        label-for="input-2">
                                                        <b-form-textarea id="input-2" v-model="form.sample_description"
                                                            placeholder="description" rows="6" required>
                                                        </b-form-textarea>
                                                    </b-form-group>
                                                    <b-button type="submit" variant="primary">Submit</b-button>
                                                </b-form> -->
                                            </div>
                                        </b-collapse>
                                    </b-col>
                                    <b-col>
                                        <DirectionalPad @up="OnNextFocalViewClick" @down="OnPreviousFocalViewClick"
                                            @right="OnArrowRightClick" @left="OnArrowLeftClick" />
                                    </b-col>
                                </b-row>
                            </b-modal>
                        </div>
                    </b-col>
                    <!-- </div> -->
                </b-row>
            </div>
        </div>
        <div v-else>
            <h5>No wells found . . .</h5>
        </div>
        <div>
            <!-- if this.plate has attribute image, show dropdown -->
            <b-row v-if="hasImages()">
                <!-- <b-row v-if="plate_name"> -->
                <b-col>
                    <b-button @click="loader('oldest')" variant="primary">Load Beginning</b-button>
                    <b-button @click="loader('newest')" variant="primary">Load Latest</b-button>
                </b-col>
                <b-col>
                    <!-- button to load beginning -->

                    <b-dropdown id="dropdown-1" :text="uuid" block variant="outline-primary" class="m-2">
                        <b-dropdown-item v-for=" ( group_id, uuid ) in plate.attributes.image_parameters.uuids"
                            :key="uuid" v-on:click="changeImageSet(uuid, group_id)">
                            {{uuid}}
                        </b-dropdown-item>
                    </b-dropdown>
                </b-col>
            </b-row>
        </div>
    </b-container>
</template>
