import React from 'react';
import {registerRoot,Composition} from 'remotion';
import {Zipper,ZIPPER_FRAMES} from './Zipper';
registerRoot(()=><Composition id="Zipper" component={Zipper} width={1080} height={1920} fps={30} durationInFrames={ZIPPER_FRAMES}/>);
