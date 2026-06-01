function data = mdp_F0_wav(data, varargin)
%MDP_F0  - MVIEW dataproc that computes running F0 estimate using YAAPT
% raw F0 and interpolated F0 are both calculated
% appends noth F0 signals to a STRUCT with just audio
% dependencies:  yaapt

% JS 07/21

% number of samples in the audio data
s = size(data(1).SIGNAL);

% gets pitch track from YAAPT
[ps, nf] = yaapt(data(1).SIGNAL, data(1).SRATE, 1, [], 0, 1);

% sample rate of pitch track
duration = s(1)./ data(1).SRATE;
sr = nf ./ duration;

% replace NaNs
%vq1 = naninterp(ps);

%find zeros
%idx = find(~vq1)

%if there is a non-zero sample preceeding the zero, 
% then calculate a linear interpolation

% replace zeros with the median non-zero f0 value in the token; this is to
% reduce the velocity increase from zero to f0 at the onset of voicing.
%vq1(vq1==0)=median(nonzeros(vq1));

%ps(ps==0)=median(nonzeros(ps));

%Robust smoothing algorithm
%vq1	= transpose(smoothn(ps,'robust' ));

% replace zeros with the median non-zero f0 value in the token; this is to
% reduce the velocity increase from zero to f0 at the onset of voicing.
%vq1(vq1==0)=median(nonzeros(vq1));

% replace zeros with linear interpolation
%vq2 = fillmissing(vq1, 'linear')

% fill outliers
%vq3 = filloutliers(vq2,'linear');

%vq4 = filloutliers(v3,'clip','movmedian',5);

% smooth signal
%vq3 = smoothn(vq2, 'robust')

% replace NANs with zero
%ps(isnan(ps))=0;

% find outliers and replace them with a linear interpolation between
% flanking values
%vq2 = filloutliers(vq1,'linear');

%vq2 = filloutliers(ps,'clip','movmedian',5);

% z-score non-zero values of pitch track
%z = zscore(nonzeros(vq1))
% identify outliers as values greater than 2 standard deviations from the
% mean
%I = abs(z)>2;
%outliers = excludedata(xq,vq1,'indices',I);

% 5 sample moving average filter
%vq4 = smooth(vq3,'moving',7);

% add pitch to the end of the struct
data(end+1) = data(1);
data(end).NAME = 'f0';
data(end).SRATE = sr;
data(end).SIGNAL = transpose(ps);
%data(end).SIGNAL = transpose(vq2);

% add interpolated f0
ps(ps==0)=NaN;
ips = smoothn(ps,'robust');

data(end+1) = data(1);
data(end).NAME = 'f0interp';
data(end).SRATE = sr;
data(end).SIGNAL = transpose(ips);
