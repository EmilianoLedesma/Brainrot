import React from 'react';
import {registerRoot,Composition} from 'remotion';
import {ShockAbsorber,SHOCK_FRAMES} from './ShockAbsorber';
registerRoot(()=><Composition id="ShockAbsorber" component={ShockAbsorber} width={1080} height={1920} fps={30} durationInFrames={SHOCK_FRAMES}/>);
