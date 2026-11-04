import React from 'react';
import {registerRoot,Composition} from 'remotion';
import {Deadbolt,DEADBOLT_FRAMES} from './Deadbolt';
registerRoot(()=><Composition id="Deadbolt" component={Deadbolt} width={1080} height={1920} fps={30} durationInFrames={DEADBOLT_FRAMES}/>);
