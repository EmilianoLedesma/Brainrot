import React from 'react';
import {registerRoot,Composition} from 'remotion';
import {SkyBlue,SKY_FRAMES} from './SkyBlue';
registerRoot(()=><Composition id="SkyBlue" component={SkyBlue} width={1080} height={1920} fps={30} durationInFrames={SKY_FRAMES}/>);
