import React from 'react';
import {registerRoot,Composition} from 'remotion';
import {MotionVideo,defaultMotionProps,FPS,MotionProps} from './Motion';
import {WorldVideo,defaultWorldProps,WorldProps} from './world/WorldVideo';

// Rendered by brainrot/motion.py and brainrot/world/render.py with --props; duration comes from the narration length.
registerRoot(()=> <>
  <Composition id="Motion" component={MotionVideo} width={1080} height={1920} fps={FPS}
    durationInFrames={30} defaultProps={defaultMotionProps}
    calculateMetadata={({props}:{props:MotionProps})=>({durationInFrames:Math.max(1,Math.ceil(props.duration*FPS))})}/>
  <Composition id="World" component={WorldVideo} width={1080} height={1920} fps={FPS}
    durationInFrames={30} defaultProps={defaultWorldProps}
    calculateMetadata={({props}:{props:WorldProps})=>({durationInFrames:Math.max(1,props.script?props.script.durationFrames:1)})}/>
</>);
