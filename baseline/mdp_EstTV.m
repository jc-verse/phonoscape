function data = mdp_EstTV(data, varargin)
%MDP_ESTTV  - MVIEW dataproc that estimates tract variables from speech using pretrained (XRMB) estimator
%
% performs acoustic to articulatory speech inversion with a feedforward DNN
% weights estimated from the XRMB using a DNN trained with Keras in Python
% network is trained to estimate the tract variables from contextualized MFCCs
%
% appends tract variables LACL(LP), LACD(LA), TBCL, TBCD, TTCL, TTCD
%
% based on G. Sivaraman's estimate_tv_xrmb.py()
%
% see also ESTTV (which does the work)

% mkt 03/18

TV = EstTV(data);

for k = 2 : length(TV),
	data(end+1) = data(end);
	switch TV(k).NAME,
		case 'LA', data(end).NAME = 'LACD';
		case 'LP', data(end).NAME = 'LACL';
		otherwise, data(end).NAME = TV(k).NAME;
	end;
	data(end).SRATE = TV(k).SRATE;
	data(end).SIGNAL = TV(k).SIGNAL;
	minS = min(data(end).SIGNAL);
	maxS = max(data(end).SIGNAL);
	spread = maxS - minS;
	data(end).SPREAD = [minS-spread*.1 maxS+spread*.1];
	data(end).NCOMPS = 1;
end;
