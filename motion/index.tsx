import React from 'react';
import {registerRoot,Composition} from 'remotion';
import {MotionVideo,defaultMotionProps,FPS,MotionProps} from './Motion';

// Rendered by brainrot/motion.py with --props; duration comes from the narration length.
registerRoot(()=> <Composition id="Motion" component={MotionVideo} width={1080} height={1920} fps={FPS}
  durationInFrames={30} defaultProps={defaultMotionProps}
  calculateMetadata={({props}:{props:MotionProps})=>({durationInFrames:Math.max(1,Math.ceil(props.duration*FPS))})}/>);
