import React from 'react';
import {registerRoot,Composition} from 'remotion';
import {Delegation,DELEGATION_FRAMES} from './Delegation';
import {Rig,RIG_FRAMES} from './Rig';
registerRoot(()=><><Composition id="Delegation" component={Delegation} width={1080} height={1920} fps={30} durationInFrames={DELEGATION_FRAMES}/><Composition id="Rig" component={Rig} width={1080} height={1920} fps={30} durationInFrames={RIG_FRAMES}/></>);
