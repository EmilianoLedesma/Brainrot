import React from 'react';
import {registerRoot,Composition} from 'remotion';
import {Birds,BIRDS_FRAMES} from './Birds';
registerRoot(()=><Composition id="Birds" component={Birds} width={1080} height={1920} fps={30} durationInFrames={BIRDS_FRAMES}/>);
