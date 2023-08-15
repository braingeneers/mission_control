<!-- d-pad CSS taken from https://codepen.io/tswone/pen/GLzZLd -->
<script>
    export default {
        name: 'DirectionalPad',
        components: {
        },
      data() {
        return {
          count: 0
        }
      },
      methods: {
        up(){
            console.log("up")
        },
        right(){
            console.log("right")
        },
        down(){
            console.log("down")
        },
        left(){
            console.log("left")
        }
      }
    }
</script>

<template>
    <div class="set">
    <nav class="d-pad">
        <!-- emit click events -->
        <a class="up" href="#" @click="$emit('up')"></a>
        <a class="right" href="#" @click="$emit('right')"></a>
        <a class="down" href="#" @click="$emit('down')"></a>
        <a class="left" href="#" @click="$emit('left')"></a>  
    </nav>
    </div>
</template>

<style lang="less">
.set {
  overflow: hidden;
  padding: 0px;
  text-align: center;
 .d-pad { margin-left: 0px; }
 .d-pad, .o-pad {
    // display: inline-block;
    transform: scale(.7);
  }
}
.set.setbg { background: #222; }
.set.setbg2 { background: #5f9837; }


@dpad-radius: 17%;
@dpad-radius-in: 20%;
@dpad-fg: #ddd;
@dpad-fg-hover: #eee;
@dpad-bg: #fff;
@arrowcolor: #aaa;
@tri-sml-a: 13px;
@tri-sml-b: 19px;
@tri-lrg-a: 13px;
@tri-lrg-b: 19px;
@dpad-arrow-shift: 5px;
@dpad-arrow-move: 35%;
.d-pad {
  position: relative;
  width: 200px;
  height: 200px;
  border-radius: 48%;
  overflow: hidden;
  &:before {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    border-radius: 5%;       
    transform: translate(-50%, -50%);
    width: 66.6%;
    height: 66.6%;
    background: @dpad-fg;
  }
  &:after {
    content: '';
    position: absolute;
    display: none;
    z-index:2;
    width: 20%;
    height: 20%;
    top: 50%;
    left: 50%;
    background: @dpad-fg;
    border-radius: 50%;   
    transform: translate(-50%, -50%);
    transition: all .25s;
    cursor: pointer;
  }
  &:hover:after {
    width: 30%;
    height: 30%;
  }  
  a {
    display:block;
    position: absolute;
    -webkit-tap-highlight-color:  rgba(255, 255, 255, 0);
    width: 33.3%;
    height: 43%;
    line-height: 40%;
    color: #fff;
    background: @dpad-fg;
    text-align: center;  
    &:hover {
      background: @dpad-fg-hover;
    }
    &:before {
      content: '';
      position: absolute;
      width: 0;
      height: 0;
      border-radius: 5px;
      border-style: solid;     
      transition: all .25s;
    }
    &:after {
      content: '';
      position: absolute;
      width: 102%;
      height: 78%;
      background: @dpad-bg;
      border-radius: @dpad-radius-in;
    }    
  }
  a.left, a.right {
    width: 43%;
    height: 33%;
    &:after {
      width: 78%;
      height: 102%;
    }    
  }
  
  a.up {
    top: 0;
    left: 50%;
    transform: translate(-50%, 0);
    border-radius: @dpad-radius @dpad-radius 50% 50%;
    &:hover {
      background: linear-gradient(0deg, @dpad-fg 0%, @dpad-fg-hover 50%);
    }
    &:after {
      left: 0;
      top: 0;
      transform: translate(-100%, 0);
      border-top-left-radius: 50%;
      pointer-events: none;
    }
    &:before {
      top: 40%;
      left: 50%;
      transform: translate(-50%, -50%);
      border-width: 0 @tri-sml-a @tri-sml-b @tri-sml-a;
      border-color: transparent transparent @arrowcolor transparent;
    }
    &:active:before {
      border-bottom-color: #333;
    }
  }
  a.up:hover:before { top: @dpad-arrow-move; }
  
  a.down {
    bottom: 0;
    left: 50%;    
    transform: translate(-50%, 0);
    border-radius: 50% 50% @dpad-radius @dpad-radius; 
    &:hover {
      background: linear-gradient(180deg, @dpad-fg 0%, @dpad-fg-hover 50%);
    }
    &:after {
      right: 0;
      bottom: 0;
      transform: translate(100%, 0);
      border-bottom-right-radius: 50%;
      pointer-events: none;
    }
    &:before {
      bottom: 40%;
      left: 50%;
      transform: translate(-50%, 50%);
      border-width: @tri-sml-b @tri-sml-a 0px @tri-sml-a;
      border-color: @arrowcolor transparent transparent transparent;
    }
    &:active:before {
      border-top-color: #333;
    }
  }
  a.down:hover:before { bottom: @dpad-arrow-move; }
  
  a.left {
    top: 50%;
    left: 0;    
    transform: translate(0, -50%);
    border-radius: @dpad-radius 50% 50% @dpad-radius;
    &:hover {
      background: linear-gradient(-90deg, @dpad-fg 0%, @dpad-fg-hover 50%);
    }
    &:after {
      left: 0;
      bottom: 0;
      transform: translate(0, 100%);
      border-bottom-left-radius: 50%;
      pointer-events: none;
    }
    &:before {
      left: 40%;
      top: 50%;
      transform: translate(-50%, -50%);
      border-width: @tri-sml-a @tri-sml-b @tri-sml-a 0;
      border-color: transparent @arrowcolor transparent transparent;
    }
    &:active:before {
      border-right-color: #333;
    }
  }
  a.left:hover:before { left: @dpad-arrow-move; }
  
  a.right {
    top: 50%;
    right: 0;    
    transform: translate(0, -50%);  
    border-radius: 50% @dpad-radius @dpad-radius 50%;
    &:hover {
      background: linear-gradient(90deg, @dpad-fg 0%, @dpad-fg-hover 50%);
    }
    &:after {
      right: 0;
      top: 0;
      transform: translate(0, -100%);
      border-top-right-radius: 50%;      
      pointer-events: none;
    }
    &:before {
      right: 40%;
      top: 50%;
      transform: translate(50%, -50%);
      border-width: @tri-sml-a 0 @tri-sml-a @tri-sml-b;
      border-color: transparent transparent transparent @arrowcolor;
    }
    &:active:before {
      border-left-color: #333;
    }
  }
  a.right:hover:before { right: @dpad-arrow-move; }  
}
.d-pad.up a.up:before { border-bottom-color: #333; }
.d-pad.down a.down:before { border-top-color: #333; }
.d-pad.left a.left:before { border-right-color: #333; }
.d-pad.right a.right:before { border-left-color: #333; }


.o-pad {
  position: relative;
  background: @dpad-fg;
  width: 200px;
  height: 200px;
  border-radius:50%;
  overflow:hidden;
  &:after {
    content: '';
    position: absolute;
    z-index: 2;
    width: 20%;
    height: 20%;
    top: 50%;
    left: 50%;
    background: #ddd;
    border-radius: 50%;   
    transform: translate(-50%, -50%);
    display: none;
    transition: all .25s;
    cursor: pointer;
  }
  &:hover:after {
    width: 30%;
    height: 30%;
  }
  a {
    display:block;
    position: absolute;
    -webkit-tap-highlight-color:  rgba(255, 255, 255, 0);
    width: 50%;
    height: 50%;
    text-align: center;  
    transform: rotate(45deg);
    border: 1px solid rgba(0,0,0,.2);
    &:before {
      content: '';
      position: absolute;
      width: 60%;
      height: 60%;
      top: 50%;
      left: 50%;
      background: rgba(255,255,255,0.1);
      border-radius: 50%;   
      transform: translate(-50%, -50%);
      transition: all .25s;
      cursor: pointer;
      display: none;
    }
    &:after {
      content: '';
      position: absolute;
      width: 0;
      height: 0;
      border-radius: 5px;
      border-style: solid;    
      transform: translate(-50%, -50%) rotate(-45deg);
      transition: all .25s;
    }
  }
  a.up {
    bottom: 50%;
    left: 50%;
    transform: translate(-50%, -20%) rotate(45deg);
    border-top-left-radius: 50%;
    z-index:1;
    &:hover {
      background: linear-gradient(315deg, rgba(255,255,255,0) 15%, rgba(255,255,255,.4) 100%);
    }
    &:before {
      left: 57%;
      top: 57%;
    }
    &:after {
      left: 53%;
      top: 53%;
      border-width: 0 @tri-lrg-a @tri-lrg-b @tri-lrg-a;
      border-color: transparent transparent @arrowcolor transparent;
    }
    &:active:after {
      border-bottom-color: #333;
    }
  }
  
  a.down {
    top: 50%;
    left: 50%;    
    transform: translate(-50%, 20%) rotate(45deg);
    border-bottom-right-radius: 50%;
    z-index:1;
    &:hover {
      background: linear-gradient(135deg, rgba(255,255,255,0) 15%, rgba(255,255,255,.4) 100%);
    }
    &:before {
      left: 43%;
      top: 43%;
    }
    &:after {
      left: 47%;
      top: 47%;
      border-width: @tri-lrg-b @tri-lrg-a 0px @tri-lrg-a;
      border-color: @arrowcolor transparent transparent transparent;
    }
    &:active:after {
      border-top-color: #333;
    }
  } 
  
  a.left {
    top: 50%;
    right: 50%;    
    transform: translate(-20%, -50%) rotate(45deg);
    border-bottom-left-radius: 50%;
    border: none;
    &:hover {
      background: linear-gradient(225deg, rgba(255,255,255,0) 15%, rgba(255,255,255,.4) 100%);
    }
    &:before {
      left: 57%;
      top: 43%;
    }
    &:after {
      left: 53%;
      top: 47%;
      border-width: @tri-lrg-a @tri-lrg-b @tri-lrg-a 0;
      border-color: transparent @arrowcolor transparent transparent;
    }
    &:active:after {
      border-right-color: #333;
    }
  }  
  
  a.right {
    top: 50%;
    left: 50%;    
    transform: translate(20%, -50%) rotate(45deg);  
    border-top-right-radius: 50%;
    border: none;
    &:hover {
      background: linear-gradient(45deg, rgba(255,255,255,0) 15%, rgba(255,255,255,.4) 100%);
    }
    &:before {
      left: 43%;
      top: 57%;
    }
    &:after {
      left: 47%;
      top: 53%;
      border-width: @tri-lrg-a 0 @tri-lrg-a @tri-lrg-b;
      border-color: transparent transparent transparent @arrowcolor;
    }    
    &:active:after {
      border-left-color: #333;
    }
  } 
  a:hover:after { left: 50%; top: 50%; }  
}

.dark {
  @c: #111;
  @c-h: #222;
  @c-t: rgba(255,255,255,.9);
  @c-t-a: #61e22d;
  .d-pad {    
    a { border-radius: 35%; }
    &:before, a { background: #111; }
    a.up:hover { background: linear-gradient(0deg, @c 0%, @c-h 50%); }
    a.right:hover { background: linear-gradient(90deg, @c 0%, @c-h 50%); }
    a.down:hover { background: linear-gradient(180deg, @c 0%, @c-h 50%); }
    a.left:hover { background: linear-gradient(-90deg, @c 0%, @c-h 50%); }
    a.up:before { border-bottom-color: @c-t; }
    a.right:before { border-left-color: @c-t; }    
    a.down:before { border-top-color: @c-t; }
    a.left:before { border-right-color: @c-t; }
    a.up:active:before { border-bottom-color: @c-t-a; }
    a.right:active:before { border-left-color: @c-t-a; }    
    a.down:active:before { border-top-color: @c-t-a; }
    a.left:active:before { border-right-color: @c-t-a; }
  }
  .o-pad {
    background: @c;
    a { border-color: rgba(255,255,255,.4); }
    a:before { display: block; }    
    &:before, a { background: @c; }
    a.up:after { border-bottom-color: @c-t; }
    a.right:after { border-left-color: @c-t; }    
    a.down:after { border-top-color: @c-t; }
    a.left:after { border-right-color: @c-t; }
    a.up:active:after { border-bottom-color: @c-t-a; }
    a.right:active:after { border-left-color: @c-t-a; }    
    a.down:active:after { border-top-color: @c-t-a; }
    a.left:active:after { border-right-color: @c-t-a; }
  }
}

.pink {
  @c: #ff1285;
  @c-h: #f366aa;
  @c-t: rgba(255,255,255,.7);
  @c-t-a: rgba(255,255,255,1);
  .d-pad {    
    &:before, a { background: @c; }
    a:after { border-radius: 30%; }
    a.up:hover { background: linear-gradient(0deg, @c 0%, @c-h 50%); }
    a.right:hover { background: linear-gradient(90deg, @c 0%, @c-h 50%); }
    a.down:hover { background: linear-gradient(180deg, @c 0%, @c-h 50%); }
    a.left:hover { background: linear-gradient(-90deg, @c 0%, @c-h 50%); }
    a.up:before { border-bottom-color: @c-t; }
    a.right:before { border-left-color: @c-t; }    
    a.down:before { border-top-color: @c-t; }
    a.left:before { border-right-color: @c-t; }
    a.up:active:before { border-bottom-color: @c-t-a; }
    a.right:active:before { border-left-color: @c-t-a; }    
    a.down:active:before { border-top-color: @c-t-a; }
    a.left:active:before { border-right-color: @c-t-a; }
  }
  .o-pad {
    background: @c;
    a { border-color: rgba(255,255,255,.6); }
    &:before, a { background: @c; }
    a.up:after { border-bottom-color: @c-t; }
    a.right:after { border-left-color: @c-t; }    
    a.down:after { border-top-color: @c-t; }
    a.left:after { border-right-color: @c-t; }
    a.up:active:after { border-bottom-color: @c-t-a; }
    a.right:active:after { border-left-color: @c-t-a; }    
    a.down:active:after { border-top-color: @c-t-a; }
    a.left:active:after { border-right-color: @c-t-a; }
  }
}

.clear {
  @c: #fff;
  @c-h: #6ea248;
  @c-bg: #5f9837;
  @c-t: #fff;
  @c-t-a: rgba(0,0,0,.6);
  .d-pad {
    border-radius: 0;
    a { border: 1px solid @c; }
    &:before, a { background: none; }
    a:after { display: none; }
    a.up:hover { background: linear-gradient(0deg, @c-bg 0%, @c-h 50%); }
    a.right:hover { background: linear-gradient(90deg, @c-bg 0%, @c-h 50%); }
    a.down:hover { background: linear-gradient(180deg, @c-bg 0%, @c-h 50%); }
    a.left:hover { background: linear-gradient(-90deg, @c-bg 0%, @c-h 50%); }
    a.up:before { border-bottom-color: @c-t; }
    a.right:before { border-left-color: @c-t; }    
    a.down:before { border-top-color: @c-t; }
    a.left:before { border-right-color: @c-t; }
    a.up:active:before { border-bottom-color: @c-t-a; }
    a.right:active:before { border-left-color: @c-t-a; }    
    a.down:active:before { border-top-color: @c-t-a; }
    a.left:active:before { border-right-color: @c-t-a; }
  }
  .o-pad {
    @c: #fff;
    background: none;
    border: 1px solid @c-t;
    a { border-color: @c-t; }
    &:before, a { background: none; }
    a.up:after { border-bottom-color: @c-t; }
    a.right:after { border-left-color: @c-t; }    
    a.down:after { border-top-color: @c-t; }
    a.left:after { border-right-color: @c-t; }
    a.up:active:after { border-bottom-color: @c-t-a; }
    a.right:active:after { border-left-color: @c-t-a; }    
    a.down:active:after { border-top-color: @c-t-a; }
    a.left:active:after { border-right-color: @c-t-a; }
  }
}

.outline {
  @c: #fff;
  @c-h: #efefef;
  @c-t: rgba(0,0,0,.1);
  .d-pad {
    border-radius: 0;
    a { border: 1px solid @c-t; }
    &:after, &:before, a { background: @c; }
    a:after { display: none; }
    a.up:hover { background: linear-gradient(0deg, @c 0%, @c-h 50%); }
    a.right:hover { background: linear-gradient(90deg, @c 0%, @c-h 50%); }
    a.down:hover { background: linear-gradient(180deg, @c 0%, @c-h 50%); }
    a.left:hover { background: linear-gradient(-90deg, @c 0%, @c-h 50%); }
    a.up:before { border-bottom-color: @c-t; }
    a.right:before { border-left-color: @c-t; }    
    a.down:before { border-top-color: @c-t; }
    a.left:before { border-right-color: @c-t; }
  }
  .o-pad {
    @c: #fff;
    background: @c;
    border: 1px solid @c-t;
    a { border-color: @c-t; }
    &:after, &:before, a { background: @c; }
    a.up:after { border-bottom-color: @c-t; }
    a.right:after { border-left-color: @c-t; }    
    a.down:after { border-top-color: @c-t; }
    a.left:after { border-right-color: @c-t; }
  }
}


.blue {
  @c: #1843ca;
  @c-h: #143cb9;
  @c-t: #ccc;
  @c-t-a: rgba(255,255,255,1);
  .d-pad {    
    &:before, a { background: @c; }
    &:after { display: block; background: @c-t; } 
    a:after { border-radius: 10%; }
    a.up:hover { background: linear-gradient(0deg, @c 0%, @c-h 50%); }
    a.right:hover { background: linear-gradient(90deg, @c 0%, @c-h 50%); }
    a.down:hover { background: linear-gradient(180deg, @c 0%, @c-h 50%); }
    a.left:hover { background: linear-gradient(-90deg, @c 0%, @c-h 50%); }
    a.up:before { border-bottom-color: @c-t; }
    a.right:before { border-left-color: @c-t; }    
    a.down:before { border-top-color: @c-t; }
    a.left:before { border-right-color: @c-t; }
    a.up:active:before { border-bottom-color: @c-t-a; }
    a.right:active:before { border-left-color: @c-t-a; }    
    a.down:active:before { border-top-color: @c-t-a; }
    a.left:active:before { border-right-color: @c-t-a; }
  }
  .o-pad {
    background: @c;
    a { border-color: rgba(255,255,255,.6); }
    &:before, a { background: @c; }
    &:after { display: block; background: #ccc; }     
    a.up:after { border-bottom-color: @c-t; }
    a.right:after { border-left-color: @c-t; }    
    a.down:after { border-top-color: @c-t; }
    a.left:after { border-right-color: @c-t; }
    a.up:active:after { border-bottom-color: @c-t-a; }
    a.right:active:after { border-left-color: @c-t-a; }    
    a.down:active:after { border-top-color: @c-t-a; }
    a.left:active:after { border-right-color: @c-t-a; }
  }
}

.setbg.white {
  @c: #fff;
  @c-t: rgba(0,0,0,.1);
  @c-t-a: rgba(0,0,0,.6);
  @c-h: #143cb9;
  .d-pad {    
    &:before, a { background: @c; }
    &:after { display: block; background: @c-t; } 
    a:after { border-radius: 40%; background: #222; }
    a.up:hover { background: @c; }
    a.right:hover { background: @c; }
    a.down:hover { background: @c; }
    a.left:hover { background: @c; }
    a.up:before { border-bottom-color: #0074D9; }
    a.right:before { border-left-color: #FF851B; }    
    a.down:before { border-top-color: #3D9970; }
    a.left:before { border-right-color: #FFDC00; }
    a.up:active:before { border-bottom-color: @c-t-a; }
    a.right:active:before { border-left-color: @c-t-a; }    
    a.down:active:before { border-top-color: @c-t-a; }
    a.left:active:before { border-right-color: @c-t-a; }
  }
  .o-pad {
    background: @c;
    a { border-color: rgba(255,255,255,.6); }
    &:before, a { background: @c; }
    &:after { display: block; background: #ccc; }     
    a.up:after { border-bottom-color: #2ECC40; }
    a.right:after { border-left-color: #85144b; }    
    a.down:after { border-top-color: #7FDBFF; }
    a.left:after { border-right-color: #B10DC9; }
    a.up:active:after { border-bottom-color: @c-t-a; }
    a.right:active:after { border-left-color: @c-t-a; }    
    a.down:active:after { border-top-color: @c-t-a; }
    a.left:active:after { border-right-color: @c-t-a; }
  }
}

.wire {
  @c: #93b4ff;
  .d-pad {    
    overflow: initial;
    border: 1px dashed @c;
    &:after { display: block; }
    &:after, &:before, a, a:after {
      background: none;
      border: 1px solid @c;
    }
    a:after { border: 1px dashed @c; }
    a.up:before { border-bottom-color: @c; }
    a.right:before { border-left-color: @c; }    
    a.down:before { border-top-color: @c; }
    a.left:before { border-right-color: @c; }
    a:hover { background: none; }
  }
  .o-pad { 
    border: 1px dashed @c;
    background: none;
    overflow: initial;  
    &:after, a:before { display: block; }    
    &:after, &:before, a, a:before {
      background: none;
      border: 1px solid @c;
    }
    a.up:after { border-bottom-color: @c; }
    a.right:after { border-left-color: @c; }    
    a.down:after { border-top-color: @c; }
    a.left:after { border-right-color: @c; }
    a:hover { background: none; }
  }
}

// set direction active state

.d-pad.up a.up:before { border-bottom-color: #333; }
.d-pad.down a.down:before { border-top-color: #333; }
.d-pad.left a.left:before { border-right-color: #333; }
.d-pad.right a.right:before { border-left-color: #333; }

.o-pad.up a.up:after { border-bottom-color: #333; }
.o-pad.down a.down:after { border-top-color: #333; }
.o-pad.left a.left:after { border-right-color: #333; }
.o-pad.right a.right:after { border-left-color: #333; }
</style>
    
