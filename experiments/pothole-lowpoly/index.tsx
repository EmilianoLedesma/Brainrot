import React from 'react';
import {registerRoot,Composition} from 'remotion';
import {Pothole,POTHOLE_FRAMES} from './Pothole';
registerRoot(()=><Composition id="Pothole" component={Pothole} width={1080} height={1920} fps={30} durationInFrames={POTHOLE_FRAMES}/>);
