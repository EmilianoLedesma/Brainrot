import React from 'react';
import {registerRoot,Composition} from 'remotion';
import {MokaCutaway,MOKA_FRAMES} from './MokaCutaway';
registerRoot(()=><Composition id="MokaCutaway" component={MokaCutaway} width={1080} height={1920} fps={30} durationInFrames={MOKA_FRAMES}/>);
