import React from 'react';
import {registerRoot,Composition} from 'remotion';
import {Zebra,ZEBRA_FRAMES} from './Zebra';
registerRoot(()=><Composition id="Zebra" component={Zebra} width={1080} height={1920} fps={30} durationInFrames={ZEBRA_FRAMES}/>);
